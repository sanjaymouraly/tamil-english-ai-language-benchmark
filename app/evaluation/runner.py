"""Benchmark runner: executes evaluation jobs end-to-end.

Responsibilities:
  * versioned prompt construction
  * provider invocation with concurrency limits
  * cost-limit enforcement (pre-run estimate + running total)
  * graceful interruption and resume
  * cross-example terminology consistency (job level)
  * persistence of job, results, and events
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from app.core.errors import CostLimitExceededError
from app.core.schemas import BenchmarkExample, JobConfig
from app.database import crud
from app.database.session import session_scope
from app.evaluation.engine import EvaluationEngine
from app.evaluation.terminology import cross_example_consistency
from app.providers.base import GenerationRequest, ProviderAdapter
from app.providers.cost import job_cost_estimate

PROMPT_VERSION = "prompt-v1"

# Per-task instruction templates (versioned as part of PROMPT_VERSION).
TASK_INSTRUCTIONS: dict[str, str] = {
    "translation_ta_to_en": "Translate the Tamil text into natural English.",
    "translation_en_to_ta": "Translate the English text into natural Tamil.",
    "code_mixed_understanding": "Understand the Tamil-English code-mixed text and respond in the target language.",
    "romanized_transliteration": "Transliterate the romanized Tamil into Tamil script and give the meaning.",
    "register_formality": "Translate, preserving the register and politeness level.",
    "instruction_following": "Follow the Tamil instruction exactly.",
    "customer_support": "Continue the customer-support conversation appropriately.",
    "business_email": "Produce the business email translation.",
    "idiom_culture": "Interpret the idiom/cultural phrase and explain its meaning.",
    "ambiguity_context": "Resolve the ambiguity using context and explain.",
    "technical_terminology": "Translate using the domain terminology consistently.",
    "summarization_rewriting": "Summarize or rewrite while preserving all facts.",
    "entities_numbers": "Translate, preserving all numbers, dates, and units exactly.",
    "long_context_multiturn": "Answer using the full conversation context.",
    "language_switching": "Respond in the requested target language and register.",
    "safety_critical": "Translate with exact preservation of all quantities and instructions.",
}


@dataclass
class RunProgress:
    completed: int = 0
    total: int = 0
    errors: int = 0
    cost_usd: float = 0.0
    stop_requested: bool = False


class BenchmarkRunner:
    """Runs evaluation jobs over a dataset with a provider."""

    def __init__(
        self,
        provider: ProviderAdapter,
        engine: EvaluationEngine | None = None,
        on_progress: Callable[[RunProgress], None] | None = None,
        stop_event: threading.Event | None = None,
    ) -> None:
        self.provider = provider
        self.engine = engine or EvaluationEngine()
        self.on_progress = on_progress
        self.stop_event = stop_event or threading.Event()

    # ------------------------------------------------------------------
    def build_prompt(self, example: BenchmarkExample) -> list[dict[str, str]]:
        target = example.target_language
        lang_name = {"ta": "Tamil", "en": "English", "ta+en": "Tamil or English"}.get(
            target, target
        )
        glossary_lines = ""
        if example.glossary:
            terms = "; ".join(f"{g.term} -> {g.translation}" for g in example.glossary)
            glossary_lines = f"\nUse this terminology consistently: {terms}."
        task = TASK_INSTRUCTIONS.get(example.category.value, "Respond appropriately.")
        system = f"You are a careful bilingual Tamil-English assistant. Respond in {lang_name}.{glossary_lines}"
        user = (
            f"{task}\n\n"
            f"Input ({example.direction}):\n{example.source_text}\n\n"
            f"Expected behavior: {example.expected_behavior}"
        )
        if example.context:
            user += f"\n\nContext: {example.context}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ------------------------------------------------------------------
    def estimate_job_cost(
        self, examples: list[BenchmarkExample], config: JobConfig
    ) -> float | None:
        return job_cost_estimate(getattr(self.provider, "model", ""), len(examples))

    # ------------------------------------------------------------------
    def run(
        self,
        examples: list[BenchmarkExample],
        config: JobConfig,
        job_id: int,
        confirm_cost: bool = False,
    ) -> dict[str, Any]:
        from app.core.config import get_settings

        settings = get_settings()
        model = getattr(self.provider, "model", "") or ""
        estimate = self.estimate_job_cost(examples, config)

        if estimate is not None and estimate > settings.max_cost_usd and not confirm_cost:
            raise CostLimitExceededError(
                f"Estimated cost ${estimate:.4f} exceeds limit ${settings.max_cost_usd:.2f}; "
                "raise the limit or pass confirm_cost=True"
            )

        total_cost = 0.0
        completed = 0
        errors = 0
        results: list[dict[str, Any]] = []
        progress = RunProgress(total=len(examples))

        # Resume support: skip examples already evaluated for this job.
        with session_scope() as session:
            existing = {r.example_id for r in crud.results_for_job(session, job_id)}

        work = [ex for ex in examples if ex.id not in existing]
        progress.total = len(examples)

        # Hard guard on request volume (TEB_MAX_REQUESTS_PER_JOB).
        if len(work) > settings.max_requests_per_job:
            raise CostLimitExceededError(
                f"job would issue {len(work)} provider requests, exceeding the configured "
                f"limit of {settings.max_requests_per_job} (TEB_MAX_REQUESTS_PER_JOB)"
            )

        max_workers = min(settings.max_concurrency, len(work) or 1)

        def _process(example: BenchmarkExample) -> dict[str, Any] | None:
            if self.stop_event.is_set():
                return None
            request = GenerationRequest(
                messages=self.build_prompt(example),
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                model=model or None,
                meta={
                    "example_id": example.id,
                    "reference": example.references[0] if example.references else "",
                },
            )
            generation = self.provider.generate(request)
            item_cost = generation.cost_usd or 0.0
            output = self.engine.evaluate(
                example, generation.text, model_id=model, job_id=str(job_id)
            )
            return {
                "example_id": example.id,
                "job_id": job_id,
                "model_id": model,
                "response_text": generation.text,
                "dimension_scores": {
                    k: v.model_dump() for k, v in output.record.dimensions.items()
                },
                "overall_score": output.record.overall_score,
                "semantic_preservation": output.record.semantic_preservation,
                "terminology_consistency": output.record.terminology_consistency,
                "passed": output.record.passed,
                "error": output.record.error,
                "duration_ms": output.record.duration_ms,
                "cost_usd": item_cost,
                "latency_ms": generation.latency_ms,
                "errors": output.errors,
            }

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_process, ex): ex for ex in work}
            for future in as_completed(futures):
                if self.stop_event.is_set():
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                example = futures[future]
                try:
                    item = future.result()
                except Exception as exc:  # record the failure, continue the job
                    errors += 1
                    item = {
                        "example_id": example.id,
                        "job_id": job_id,
                        "model_id": model,
                        "response_text": "",
                        "dimension_scores": {},
                        "overall_score": None,
                        "semantic_preservation": None,
                        "terminology_consistency": None,
                        "passed": None,
                        "error": f"{type(exc).__name__}: {exc}",
                        "duration_ms": 0,
                        "cost_usd": 0.0,
                        "latency_ms": 0,
                        "errors": [str(exc)],
                    }
                if item is not None:
                    results.append(item)
                    total_cost += item.get("cost_usd") or 0.0
                    completed += 1
                    progress.completed = completed
                    progress.cost_usd = total_cost
                    progress.errors = errors
                    if self.on_progress:
                        self.on_progress(progress)

        # Persist results in dataset order so stored results are deterministic
        # regardless of the order in which provider calls completed.
        dataset_order = {ex.id: i for i, ex in enumerate(examples)}
        results.sort(key=lambda item: dataset_order.get(item["example_id"], len(dataset_order)))

        # Persist results transactionally.
        with session_scope() as session:
            for item in results:
                crud.add_result(
                    session,
                    {
                        "job_id": job_id,
                        "example_id": item["example_id"],
                        "model_id": item["model_id"],
                        "response_text": item["response_text"],
                        "scores_json": item["dimension_scores"],
                        "overall_score": item["overall_score"],
                        "semantic_preservation": item["semantic_preservation"],
                        "terminology_consistency": item["terminology_consistency"],
                        "passed": (1 if item["passed"] else 0)
                        if item["passed"] is not None
                        else None,
                        "error": item["error"],
                        "duration_ms": item["duration_ms"],
                    },
                )

        # Job-level terminology consistency across all responses.
        triples = []
        by_id = {ex.id: ex for ex in examples}
        for item in results:
            ex = by_id.get(item["example_id"])
            if ex:
                triples.append((ex, item["response_text"], ex.glossary))
        consistency = cross_example_consistency(triples)

        return {
            "job_id": job_id,
            "completed": completed,
            "errors": errors,
            "total_cost_usd": round(total_cost, 6),
            "terminology_consistency": consistency,
            "results": results,
        }

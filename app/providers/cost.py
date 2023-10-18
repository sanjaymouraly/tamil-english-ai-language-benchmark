"""Cost estimation for known models (USD per 1M tokens).

Prices are approximate public list prices as of 2026 and are used
ONLY for estimation. Local models cost 0. Unknown models return
None (unavailable) rather than a misleading guess.
"""

from __future__ import annotations

# (input_usd_per_mtok, output_usd_per_mtok)
PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-2024-11-20": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-nano": (0.10, 0.40),
    # Anthropic
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-7-sonnet-20250219": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    # Common OpenRouter-hosted models (approximate)
    "meta-llama/llama-3.3-70b-instruct": (0.88, 0.88),
    "google/gemini-2.0-flash-001": (0.10, 0.40),
    "google/gemini-2.5-flash": (0.30, 2.50),
}

LOCAL_MODELS = {"llama3.1", "llama3.2", "mistral", "gemma2", "local-model", ""}

#: Families that are almost always served locally when they carry no
#: ``provider/`` prefix. OpenRouter-style ids such as ``qwen/qwen-2.5-72b``
#: contain a slash and are treated as hosted (priced) models instead.
LOCAL_FAMILY_PREFIXES = ("llama", "mistral", "gemma", "phi", "qwen")


def _is_local_model(model_id: str) -> bool:
    if model_id in LOCAL_MODELS:
        return True
    if "/" in model_id:  # hosted namespace, e.g. meta-llama/llama-3.3-70b
        return False
    return model_id.startswith(LOCAL_FAMILY_PREFIXES)


def estimate_cost_usd(
    model_id: str, prompt_tokens: int | None, completion_tokens: int | None
) -> float | None:
    """Estimated cost in USD, or None when pricing is unknown."""
    if _is_local_model(model_id):
        return 0.0
    pricing = PRICING.get(model_id)
    if pricing is None:
        # Match only longer, more specific known ids (e.g. a dated snapshot such
        # as 'gpt-4o-mini-2024-07-18' matches the 'gpt-4o-mini' price). We do NOT
        # match in the other direction: a short unknown id like 'gpt' must not
        # inherit an unrelated model's price.
        candidates = [k for k in PRICING if model_id.startswith(k)]
        if candidates:
            pricing = PRICING[max(candidates, key=len)]
    if pricing is None or prompt_tokens is None or completion_tokens is None:
        return None
    input_cost = (prompt_tokens / 1_000_000) * pricing[0]
    output_cost = (completion_tokens / 1_000_000) * pricing[1]
    return round(input_cost + output_cost, 6)


def job_cost_estimate(
    model_id: str, n_examples: int, avg_prompt_tokens: int = 250, avg_completion_tokens: int = 150
) -> float | None:
    """Estimate the total cost of a job before running it."""
    per = estimate_cost_usd(model_id, avg_prompt_tokens, avg_completion_tokens)
    if per is None:
        return None
    return round(per * n_examples, 4)

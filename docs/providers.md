# Provider adapters

## Design principles

- **Credentials before use.** A live provider is only constructed when its
  credentials are present; otherwise the run fails fast with a clear error.
- **Cost-aware.** Every call is costed (`app/providers/cost.py`) and bounded by
  `TEB_MAX_COST_USD` (default $1.00). `teb eval run` prints a pre-run estimate.
- **Resilient.** Bounded retries with exponential backoff and jitter
  (`app/providers/retry.py`).
- **Cacheable.** Responses are cached by a SHA-256 of the request
  (`app/providers/cache.py`), so re-runs are cheap. Disable with
  `TEB_CACHE_ENABLED=false`.
- **Honest.** Unsupported capabilities are reported as unavailable, never
  silently faked. A model that returns no usable answer raises a clear error
  rather than being silently scored as empty.

## Built-in providers

| Provider | Cost | Network | Notes |
| --- | --- | --- | --- |
| `mock` | $0 | No | Deterministic, hash-bucketed flaws; reference read from `request.meta` only |
| `offline` | $0 | No | Replays a JSONL of prior responses keyed by `example_id` |
| `openai` | per-token | Yes | OpenAI API (`api.openai.com`); needs API credits |
| `anthropic` | per-token | Yes | Anthropic Claude REST API (httpx, no SDK required) |
| `openrouter` | per-token | Yes | One key, many hosted models |
| `ollama` | $0 | localhost | Local model server (OpenAI-compatible endpoint) |
| `lmstudio` | $0 | localhost | Local LM Studio server |
| `custom` | varies | Yes | Any OpenAI-compatible endpoint (vLLM, LiteLLM, Azure, Groq, …) |

### Easy connect

The dashboard's **AI Providers — Easy Connect** page (and
`app/providers/presets.py`) offers presets for OpenAI/ChatGPT API, Anthropic
Claude, OpenRouter, Groq, Together, DeepSeek, a generic custom endpoint, Ollama,
LM Studio, and the offline providers. Each preset can be tested for connectivity,
can discover the models the endpoint actually serves, and can be saved to a
local, git-ignored `.env`.

### Reference handling

The mock and offline providers receive the reference text through
`request.meta` — **never** through the live prompt — so live providers cannot
accidentally be given the answer.

## Credentials

Live providers read credentials from environment variables (see `.env.example`).
Both the bare name and the `TEB_`-prefixed name are accepted; the prefixed form
takes precedence:

```bash
# either of these works
export OPENAI_API_KEY=sk-...
export TEB_OPENAI_API_KEY=sk-...

export TEB_OPENAI_BASE_URL=https://api.openai.com/v1
export ANTHROPIC_API_KEY=sk-ant-...
```

Keys are never printed or committed. `app/core/config.py` exposes a
`redacted_view()` that masks secrets, and the logging `RedactingFilter` strips
secrets from emitted text.

## Adding a provider

1. Subclass `ProviderAdapter` (`app/providers/base.py`) and implement
   `generate(request: GenerationRequest) -> GenerationResult`,
   `test_connection()`, and `estimate_cost(prompt_tokens, completion_tokens)`.
2. Set the class attribute `name`, and accept a `model` (and `timeout`) in
   `__init__`.
3. Register it in `app/providers/registry.py` (and add a preset in
   `app/providers/presets.py` if it is user-facing).
4. Add a credential check so the registry reports it as configured only when its
   secrets are present.
5. Add a mocked unit test in `tests/unit/test_providers.py`.

## Verify before you spend

```bash
teb providers list                        # configured/unconfigured status
teb providers test mock                   # smoke-test a provider (mock is free)
teb providers test ollama --model <name>  # test a specific model
teb providers discover ollama             # list models the server actually serves
teb providers test openai                 # only runs if an OpenAI key is set
```

## Notes on local and reasoning models

- Local servers (Ollama, LM Studio) report `$0.00` cost.
- "Reasoning" models (e.g. `qwen3`) emit a thinking trace before the answer. If
  the token budget is exhausted by the trace the answer comes back empty; TEB
  raises an explicit error telling you to raise `--max-tokens` rather than
  recording a misleadingly low score.
- `TEB_REQUEST_TIMEOUT_SECONDS` (default 60) applies to every live provider
  call; raise it for slow local models.

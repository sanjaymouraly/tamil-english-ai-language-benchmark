"""Provider presets for the "easy connect" setup flow.

Each preset describes how to wire one concrete AI vendor into the platform:
which adapter to use, the base URL, a sensible default model, and which
environment variables the UI should write when the user clicks *Save*.

Presets never contain secrets. Keys are supplied by the user at runtime and are
written only to the local, git-ignored ``.env`` file.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    label: str
    #: Registered provider name understood by :class:`ProviderRegistry`.
    provider: str
    #: Human-facing kind: "offline", "local", or "cloud".
    kind: str
    base_url: str = ""
    model: str = ""
    #: Environment variables to write when saving, as {env_var: value_key}.
    #: ``value_key`` is one of "base_url", "model", "api_key".
    env_vars: dict[str, str] = field(default_factory=dict)
    needs_key: bool = False
    cost_note: str = ""
    docs_url: str = ""
    setup_hint: str = ""


PRESETS: list[ProviderPreset] = [
    ProviderPreset(
        id="mock",
        label="Deterministic mock (offline demo, $0.00)",
        provider="mock",
        kind="offline",
        model="teb-mock-v1",
        cost_note="$0.00 — no network, no API key. Reference behaviour only.",
        setup_hint="Use this to try the full workflow without any credentials.",
    ),
    ProviderPreset(
        id="offline",
        label="Offline replay (imported responses)",
        provider="offline",
        kind="offline",
        cost_note="$0.00 — replays model responses you imported yourself.",
        setup_hint="Import responses with `teb eval responses-import responses.jsonl`.",
    ),
    ProviderPreset(
        id="ollama",
        label="Ollama (local model server)",
        provider="ollama",
        kind="local",
        base_url="http://localhost:11434/v1",
        model="",
        env_vars={"OLLAMA_BASE_URL": "base_url", "OLLAMA_MODEL": "model"},
        cost_note="$0.00 — runs on your machine.",
        docs_url="https://ollama.com",
        setup_hint="Install Ollama, then `ollama pull <model>`. Discover installed models below.",
    ),
    ProviderPreset(
        id="lmstudio",
        label="LM Studio (local, OpenAI-compatible)",
        provider="lmstudio",
        kind="local",
        base_url="http://localhost:1234/v1",
        model="local-model",
        env_vars={"LMSTUDIO_BASE_URL": "base_url", "LMSTUDIO_MODEL": "model"},
        cost_note="$0.00 — runs on your machine.",
        docs_url="https://lmstudio.ai",
        setup_hint="Start the LM Studio local server, then pick the loaded model.",
    ),
    ProviderPreset(
        id="openai",
        label="OpenAI API (ChatGPT API) — paid, needs API credits",
        provider="openai",
        kind="cloud",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        env_vars={
            "OPENAI_API_KEY": "api_key",
            "OPENAI_BASE_URL": "base_url",
            "OPENAI_MODEL": "model",
        },
        needs_key=True,
        cost_note="Paid per token. gpt-4o-mini is the cheapest sensible default.",
        docs_url="https://platform.openai.com/api-keys",
        setup_hint=(
            "Requires an API key from platform.openai.com. A ChatGPT Plus "
            "subscription does NOT include API credits."
        ),
    ),
    ProviderPreset(
        id="anthropic",
        label="Anthropic Claude API — paid",
        provider="anthropic",
        kind="cloud",
        base_url="https://api.anthropic.com",
        model="claude-3-5-haiku-20241022",
        env_vars={
            "ANTHROPIC_API_KEY": "api_key",
            "ANTHROPIC_BASE_URL": "base_url",
            "ANTHROPIC_MODEL": "model",
        },
        needs_key=True,
        cost_note="Paid per token. Haiku is the cheapest Claude tier.",
        docs_url="https://console.anthropic.com/settings/keys",
        setup_hint="Create an API key in the Anthropic Console.",
    ),
    ProviderPreset(
        id="openrouter",
        label="OpenRouter (one key, many models)",
        provider="openrouter",
        kind="cloud",
        base_url="https://openrouter.ai/api/v1",
        model="google/gemini-2.0-flash-001",
        env_vars={
            "OPENROUTER_API_KEY": "api_key",
            "OPENROUTER_BASE_URL": "base_url",
            "OPENROUTER_MODEL": "model",
        },
        needs_key=True,
        cost_note="Paid per token; pricing varies per model. Model must be set.",
        docs_url="https://openrouter.ai/keys",
        setup_hint="Pick any model id from openrouter.ai/models.",
    ),
    ProviderPreset(
        id="groq",
        label="Groq (fast, OpenAI-compatible) — via custom",
        provider="custom",
        kind="cloud",
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        env_vars={
            "CUSTOM_API_KEY": "api_key",
            "CUSTOM_BASE_URL": "base_url",
            "CUSTOM_MODEL": "model",
        },
        needs_key=True,
        cost_note="Paid/free tier per token; see Groq pricing.",
        docs_url="https://console.groq.com/keys",
        setup_hint="Uses the generic OpenAI-compatible 'custom' provider.",
    ),
    ProviderPreset(
        id="together",
        label="Together AI (OpenAI-compatible) — via custom",
        provider="custom",
        kind="cloud",
        base_url="https://api.together.xyz/v1",
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        env_vars={
            "CUSTOM_API_KEY": "api_key",
            "CUSTOM_BASE_URL": "base_url",
            "CUSTOM_MODEL": "model",
        },
        needs_key=True,
        cost_note="Paid per token; see Together pricing.",
        docs_url="https://api.together.xyz/settings/api-keys",
        setup_hint="Uses the generic OpenAI-compatible 'custom' provider.",
    ),
    ProviderPreset(
        id="deepseek",
        label="DeepSeek (OpenAI-compatible) — via custom",
        provider="custom",
        kind="cloud",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        env_vars={
            "CUSTOM_API_KEY": "api_key",
            "CUSTOM_BASE_URL": "base_url",
            "CUSTOM_MODEL": "model",
        },
        needs_key=True,
        cost_note="Low-cost paid API; see DeepSeek pricing.",
        docs_url="https://platform.deepseek.com/api_keys",
        setup_hint="Uses the generic OpenAI-compatible 'custom' provider.",
    ),
    ProviderPreset(
        id="custom",
        label="Custom OpenAI-compatible endpoint (vLLM, LiteLLM, Azure, …)",
        provider="custom",
        kind="cloud",
        base_url="",
        model="",
        env_vars={
            "CUSTOM_API_KEY": "api_key",
            "CUSTOM_BASE_URL": "base_url",
            "CUSTOM_MODEL": "model",
        },
        needs_key=True,
        cost_note="Cost depends on your endpoint; unknown models report 'unavailable'.",
        setup_hint="Point at any server exposing the /chat/completions API.",
    ),
]

PRESETS_BY_ID: dict[str, ProviderPreset] = {p.id: p for p in PRESETS}


def get_preset(preset_id: str) -> ProviderPreset | None:
    return PRESETS_BY_ID.get(preset_id)

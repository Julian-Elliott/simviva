"""
_elevenlabs.py — Shared helpers for ElevenLabs Conversational AI agent API.

Used by agent_push.py and agent_pull.py.
"""

import json
import os
import urllib.error
import urllib.request

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
AGENT_ID = os.environ.get("ELEVENLABS_AGENT_ID", "").strip()


def require_env():
    """Abort with a helpful message if credentials are missing."""
    missing = []
    if not API_KEY:
        missing.append("ELEVENLABS_API_KEY")
    if not AGENT_ID:
        missing.append("ELEVENLABS_AGENT_ID")
    if missing:
        raise SystemExit(
            f"Error: {', '.join(missing)} not set.\n"
            "Run:  source .env && python3 scripts/<script>.py"
        )


def agent_url() -> str:
    return f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}"


def get_agent() -> dict:
    """GET the full agent configuration from ElevenLabs."""
    require_env()
    req = urllib.request.Request(agent_url(), headers={"xi-api-key": API_KEY})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(
            f"GET {agent_url()} failed ({e.code} {e.reason})\n{body}"
        ) from None
    except urllib.error.URLError as e:
        raise SystemExit(
            f"GET {agent_url()} — network error: {e.reason}"
        ) from None
    return json.loads(resp.read())


def patch_agent(payload: dict) -> dict:
    """PATCH the agent with the given payload and return the updated config."""
    require_env()
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        agent_url(),
        data=data,
        headers={"xi-api-key": API_KEY, "Content-Type": "application/json"},
        method="PATCH",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(
            f"PATCH {agent_url()} failed ({e.code} {e.reason})\n{body}"
        ) from None
    except urllib.error.URLError as e:
        raise SystemExit(
            f"PATCH {agent_url()} — network error: {e.reason}"
        ) from None
    return json.loads(resp.read())


# ── Extraction helpers ──

def extract_prompt(agent: dict) -> str:
    try:
        return agent["conversation_config"]["agent"]["prompt"]["prompt"]
    except (KeyError, TypeError):
        return ""


def extract_first_message(agent: dict) -> str:
    try:
        return agent["conversation_config"]["agent"]["first_message"] or ""
    except (KeyError, TypeError):
        return ""


def extract_language(agent: dict) -> str:
    try:
        return agent["conversation_config"]["agent"].get("language", "")
    except (KeyError, TypeError):
        return ""


def extract_llm(agent: dict) -> dict:
    try:
        p = agent["conversation_config"]["agent"]["prompt"]
        return {
            "provider": p.get("llm", ""),
            "model": p.get("model", ""),
            "temperature": p.get("temperature"),
            "max_tokens": p.get("max_tokens"),
        }
    except (KeyError, TypeError):
        return {}


def extract_voice(agent: dict) -> dict:
    try:
        tts = agent["conversation_config"]["tts"]
        return {
            "voice_id": tts.get("voice_id", ""),
            "model_id": tts.get("model_id", ""),
            "stability": tts.get("stability"),
            "similarity_boost": tts.get("similarity_boost"),
            "style": tts.get("style"),
            "speed": tts.get("speed"),
            "optimize_streaming_latency": tts.get("optimize_streaming_latency"),
        }
    except (KeyError, TypeError):
        return {}


def extract_data_collection(agent: dict) -> dict:
    """Pull out data collection fields, stripping API-added defaults."""
    raw = agent.get("platform_settings", {}).get("data_collection", {})
    # The API returns extra fields with default values (enum: null,
    # is_system_provided: false, etc.).  Strip them so local files stay
    # minimal and diffs aren't noisy.
    api_defaults = {
        "enum": None,
        "is_system_provided": False,
        "dynamic_variable": "",
        "constant_value": "",
    }
    cleaned = {}
    for field_name, field_def in raw.items():
        if not isinstance(field_def, dict):
            cleaned[field_name] = field_def
            continue
        cleaned[field_name] = {
            k: v for k, v in field_def.items()
            if k not in api_defaults or v != api_defaults[k]
        }
    return cleaned


def extract_dynamic_variables(agent: dict) -> dict:
    """Pull out dynamic variable placeholder defaults.

    The API stores these at conversation_config.agent.dynamic_variables
    (NOT under prompt), wrapped in {"dynamic_variable_placeholders": {...}}.
    We flatten to just the placeholders dict for local config.
    """
    try:
        dv = agent["conversation_config"]["agent"].get("dynamic_variables", {}) or {}
        # API wraps in {"dynamic_variable_placeholders": {…}} — unwrap
        return dv.get("dynamic_variable_placeholders", dv)
    except (KeyError, TypeError):
        return {}

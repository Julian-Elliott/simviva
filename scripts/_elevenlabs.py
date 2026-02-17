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
        return dv.get("dynamic_variable_placeholders") or {}
    except (KeyError, TypeError):
        return {}


def extract_turn(agent: dict) -> dict:
    """Pull out turn configuration (timeout, eagerness, soft timeout)."""
    try:
        turn = agent["conversation_config"].get("turn", {})
        if not turn:
            return {}
        result = {}
        for key in ("turn_timeout", "silence_end_call_timeout",
                     "soft_timeout_config", "turn_eagerness"):
            if key in turn:
                result[key] = turn[key]
        return result
    except (KeyError, TypeError):
        return {}


def extract_conversation(agent: dict) -> dict:
    """Pull out conversation settings (client events, max duration)."""
    try:
        conv = agent["conversation_config"].get("conversation", {})
        if not conv:
            return {}
        result = {}
        for key in ("max_duration_seconds", "client_events"):
            if key in conv:
                result[key] = conv[key]
        return result
    except (KeyError, TypeError):
        return {}


def extract_tools(agent: dict) -> list:
    """Pull out tools list (system tools like skip_turn, end_call)."""
    try:
        tools = agent["conversation_config"]["agent"]["prompt"].get("tools", [])
        return tools or []
    except (KeyError, TypeError):
        return []


def extract_supported_voices(agent: dict) -> list:
    """Pull out multi-voice configuration."""
    try:
        voices = agent["conversation_config"]["tts"].get("supported_voices", [])
        return voices or []
    except (KeyError, TypeError):
        return []


def extract_pronunciation_locators(agent: dict) -> list:
    """Pull out pronunciation dictionary locators."""
    try:
        locs = agent["conversation_config"]["tts"].get(
            "pronunciation_dictionary_locators", [])
        return locs or []
    except (KeyError, TypeError):
        return []


def extract_evaluation_criteria(agent: dict) -> list:
    """Pull out success evaluation criteria."""
    try:
        ev = agent.get("platform_settings", {}).get("evaluation", {})
        return ev.get("criteria", []) or []
    except (KeyError, TypeError):
        return []


def extract_asr(agent: dict) -> dict:
    """Pull out ASR (speech recognition) config including keywords."""
    try:
        asr = agent["conversation_config"].get("asr", {})
        if not asr:
            return {}
        result = {}
        for key in ("quality", "provider", "keywords"):
            if key in asr:
                result[key] = asr[key]
        return result
    except (KeyError, TypeError):
        return {}


# ── Workflow helpers ──

PROMPT_FILE_PREFIX = "__PROMPT_FILE__:"


def extract_workflow(agent: dict):
    """Extract the workflow definition (nodes + edges) if one exists.

    Returns the workflow dict, or None when the agent has no workflow
    (single-agent mode).
    """
    wf = agent.get("workflow")
    if not wf or not isinstance(wf, dict):
        return None
    # Treat empty workflow structures as absent
    if not wf.get("nodes") and not wf.get("edges"):
        return None
    return wf


def node_slug(node: dict) -> str:
    """Derive a filesystem-safe slug from a workflow node's name or id.

    Examples: "WELCOME" -> "welcome", "EXAMINER 1" -> "examiner_1"
    """
    raw = node.get("name", "") or node.get("id", "unknown")
    slug = raw.lower().strip()
    slug = "".join(c if c.isalnum() or c == "_" else "_" for c in slug)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "unnamed"


# Candidate key-paths where a subagent node's prompt text might live
# in the ElevenLabs API response.  We try each in order.
_NODE_PROMPT_PATHS = (
    ("data", "agent", "prompt", "prompt"),
    ("data", "prompt", "prompt"),
    ("data", "system_prompt"),
    ("config", "agent", "prompt", "prompt"),
    ("config", "prompt", "prompt"),
    ("config", "system_prompt"),
    ("agent_config_override", "prompt", "prompt"),
    ("agent_config_override", "system_prompt"),
)


def _walk_path(obj, path):
    """Navigate a nested dict by a tuple of keys.  Returns None on miss."""
    for key in path:
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        else:
            return None
    return obj


def _set_path(obj, path, value):
    """Set a value inside a nested dict, creating intermediate dicts."""
    for key in path[:-1]:
        if key not in obj or not isinstance(obj.get(key), dict):
            obj[key] = {}
        obj = obj[key]
    obj[path[-1]] = value


def find_node_prompt(node: dict):
    """Locate the system-prompt override inside a workflow node.

    Returns (prompt_text, key_path) or (None, None).
    The *key_path* can be reused with set_node_prompt().
    """
    for path in _NODE_PROMPT_PATHS:
        val = _walk_path(node, path)
        if isinstance(val, str) and val.strip():
            return val, path
    return None, None


def set_node_prompt(node: dict, path: tuple, text: str):
    """Write *text* into a node at the given key *path*."""
    _set_path(node, path, text)

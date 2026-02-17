#!/usr/bin/env python3
"""
agent_push.py — Push local agent_config/ to the ElevenLabs agent.

Reads all config files from agent_config/ and PATCHes the live agent
so it matches.

Config files (required):
  system_prompt.md        — system prompt
  data_collection.json    — post-call data extraction fields
  settings.json           — name, LLM, voice, ASR keywords, dynamic vars

Config files (optional):
  conversation_flow.json  — turn timeout, eagerness, client events
  tools.json              — system tools (skip_turn, end_call)
  supported_voices.json   — multi-voice configuration
  evaluation_criteria.json— success evaluation criteria
  pronunciation_locator.json — pronunciation dictionary reference
  workflow.json           — ElevenLabs Workflow definition + nodes/*/prompt.md

Usage:
  source .env && python3 scripts/agent_push.py
  source .env && python3 scripts/agent_push.py --dry-run
  source .env && python3 scripts/agent_push.py --branch <name>
  source .env && python3 scripts/agent_push.py --branch <name> --dry-run
"""

import json
import os
import sys

# Allow importing the shared helpers from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _elevenlabs as api

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(REPO_ROOT, "agent_config")


def _read_json(path):
    """Read a JSON file, returning None if it doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_config() -> dict:
    """Read all config files and return a structured dict."""
    prompt_path = os.path.join(CONFIG_DIR, "system_prompt.md")
    dc_path = os.path.join(CONFIG_DIR, "data_collection.json")
    settings_path = os.path.join(CONFIG_DIR, "settings.json")

    missing = [p for p in (prompt_path, dc_path, settings_path) if not os.path.exists(p)]
    if missing:
        raise SystemExit(
            "Missing config files:\n" + "\n".join("  " + p for p in missing)
        )

    with open(prompt_path, encoding="utf-8") as f:
        prompt = f.read().strip()

    with open(dc_path, encoding="utf-8") as f:
        data_collection = json.load(f)

    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)

    # Optional config files — each defaults to empty
    conversation_flow = _read_json(os.path.join(CONFIG_DIR, "conversation_flow.json")) or {}
    tools = _read_json(os.path.join(CONFIG_DIR, "tools.json")) or []
    supported_voices = _read_json(os.path.join(CONFIG_DIR, "supported_voices.json")) or []
    evaluation_criteria = _read_json(os.path.join(CONFIG_DIR, "evaluation_criteria.json")) or []
    pronunciation_locator = _read_json(os.path.join(CONFIG_DIR, "pronunciation_locator.json")) or {}

    # Workflow (optional — only present when using ElevenLabs Workflows)
    wf_path = os.path.join(CONFIG_DIR, "workflow.json")
    workflow = None
    if os.path.exists(wf_path):
        with open(wf_path, encoding="utf-8") as f:
            workflow = json.load(f)
        # Inject prompt text from node .md files, replacing file markers
        for node in workflow.get("nodes", []):
            node_prompt, path = api.find_node_prompt(node)
            if isinstance(node_prompt, str) and node_prompt.startswith(api.PROMPT_FILE_PREFIX):
                rel = node_prompt[len(api.PROMPT_FILE_PREFIX):]
                try:
                    fpath = api.safe_resolve(CONFIG_DIR, rel)
                except ValueError as e:
                    raise SystemExit("Refusing to read: {}".format(e))
                if not os.path.exists(fpath):
                    slug = api.node_slug(node)
                    raise SystemExit(
                        "Missing prompt file for node '{}': {}\n"
                        "Every __PROMPT_FILE__ marker must resolve to an existing file.\n"
                        "Create the file or run agent_pull.py to regenerate it.".format(slug, rel)
                    )
                with open(fpath, encoding="utf-8") as f:
                    api.set_node_prompt(node, path, f.read().strip())

    return {
        "prompt": prompt,
        "data_collection": data_collection,
        "settings": settings,
        "workflow": workflow,
        "conversation_flow": conversation_flow,
        "tools": tools,
        "supported_voices": supported_voices,
        "evaluation_criteria": evaluation_criteria,
        "pronunciation_locator": pronunciation_locator,
    }


def build_payload(config: dict) -> dict:
    """Build the PATCH payload from local config."""
    prompt = config["prompt"]
    data_collection = config["data_collection"]
    settings = config["settings"]
    workflow = config.get("workflow")
    conversation_flow = config.get("conversation_flow", {})
    tools = config.get("tools", [])
    supported_voices = config.get("supported_voices", [])
    evaluation_criteria = config.get("evaluation_criteria", [])
    pronunciation_locator = config.get("pronunciation_locator", {})

    llm = settings.get("llm", {})
    voice = settings.get("voice", {})
    asr = settings.get("asr", {})

    # Build the agent prompt section (includes tools)
    agent_prompt = {
        "prompt": prompt,
        "llm": llm.get("provider"),
        "model": llm.get("model") or None,
        "temperature": llm.get("temperature"),
        "max_tokens": llm.get("max_tokens"),
    }
    if tools:
        agent_prompt["tools"] = tools

    # Build TTS section — only include fields with explicit values
    tts = {
        k: v for k, v in {
            "voice_id": voice.get("voice_id"),
            "model_id": voice.get("model_id"),
            "stability": voice.get("stability"),
            "similarity_boost": voice.get("similarity_boost"),
            "style": voice.get("style"),
            "speed": voice.get("speed"),
            "optimize_streaming_latency": voice.get("optimize_streaming_latency"),
        }.items() if v is not None
    }
    if supported_voices:
        tts["supported_voices"] = supported_voices

    # Pronunciation dictionary locator — only if we have a valid ID
    pron_id = pronunciation_locator.get("pronunciation_dictionary_id")
    if pron_id:
        tts["pronunciation_dictionary_locators"] = [{
            "pronunciation_dictionary_id": pron_id,
            "version_id": pronunciation_locator.get("version_id"),
        }]

    # Build conversation_config
    conversation_config = {
        "agent": {
            "prompt": agent_prompt,
            "first_message": settings.get("first_message"),
            "language": settings.get("language"),
            "dynamic_variables": {
                "dynamic_variable_placeholders": settings.get("dynamic_variables", {}),
            },
        },
        "tts": tts,
    }

    # Turn settings (from conversation_flow.json)
    turn = conversation_flow.get("turn", {})
    if turn:
        # Strip disabled soft_timeout_config — the API rejects empty strings
        soft = turn.get("soft_timeout_config", {})
        if soft and soft.get("timeout_seconds", -1) == -1:
            turn = {k: v for k, v in turn.items() if k != "soft_timeout_config"}
        conversation_config["turn"] = turn

    # Conversation settings — client events, max duration
    conv = conversation_flow.get("conversation", {})
    if conv:
        conversation_config["conversation"] = conv

    # ASR keywords (from settings.json)
    if asr:
        conversation_config["asr"] = asr

    # Platform settings
    platform_settings = {
        "data_collection": data_collection,
    }
    if evaluation_criteria:
        platform_settings["evaluation"] = {
            "criteria": evaluation_criteria,
        }

    payload = {
        "name": settings.get("name"),
        "conversation_config": conversation_config,
        "platform_settings": platform_settings,
    }

    if workflow:
        payload["workflow"] = workflow

    return payload


def summarise_payload(config: dict):
    """Print a human-readable summary of what will be pushed."""
    settings = config["settings"]
    prompt = config["prompt"]
    data_collection = config["data_collection"]
    workflow = config.get("workflow")
    conversation_flow = config.get("conversation_flow", {})
    tools = config.get("tools", [])
    supported_voices = config.get("supported_voices", [])
    evaluation_criteria = config.get("evaluation_criteria", [])

    llm = settings.get("llm", {})
    voice = settings.get("voice", {})
    asr = settings.get("asr", {})
    turn = conversation_flow.get("turn", {})

    print("  Name:           {}".format(settings.get("name")))
    print("  Language:       {}".format(settings.get("language")))
    print("  LLM:            {} (temp={})".format(llm.get("provider"), llm.get("temperature")))
    print("  Voice:          {} ({})".format(voice.get("voice_id"), voice.get("model_id")))
    print("  Speed:          {}".format(voice.get("speed", 1.0)))
    print("  System prompt:  {} chars, ~{} words".format(len(prompt), len(prompt.split())))
    print("  Data fields:    {}".format(list(data_collection.keys())))
    dv = settings.get("dynamic_variables", {})
    ellip = "\u2026" if len(dv) > 5 else ""
    print("  Dyn variables:  {} ({}{})".format(len(dv), ", ".join(sorted(dv)[:5]), ellip))
    first_msg = settings.get("first_message", "")[:60]
    print("  First message:  {}...".format(first_msg))

    # New config sections
    if turn:
        print("  Turn timeout:   {}s (eagerness={})".format(
            turn.get("turn_timeout", "?"), turn.get("turn_eagerness", "?")))
        soft = turn.get("soft_timeout_config", {})
        print("  Soft timeout:   {}".format(
            "disabled" if soft.get("timeout_seconds", -1) == -1 else "{}s".format(soft["timeout_seconds"])))

    conv = conversation_flow.get("conversation", {})
    if conv:
        events = conv.get("client_events", [])
        print("  Client events:  {}".format(events))
        print("  Max duration:   {}s".format(conv.get("max_duration_seconds", "?")))

    if tools:
        tool_names = [t.get("name", "?") for t in tools]
        print("  System tools:   {}".format(tool_names))

    if supported_voices:
        labels = [v.get("label", "?") for v in supported_voices]
        print("  Multi-voice:    {}".format(labels))

    if asr.get("keywords"):
        print("  ASR keywords:   {} terms".format(len(asr["keywords"])))

    if evaluation_criteria:
        names = [c.get("name", "?") for c in evaluation_criteria]
        print("  Eval criteria:  {}".format(names))

    if workflow:
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])
        print("  Workflow:       {} nodes, {} edges".format(len(nodes), len(edges)))
    else:
        print("  Workflow:       none (single-agent mode)")


def main():
    dry_run = "--dry-run" in sys.argv

    # Parse --branch <name> argument
    branch_name = None
    if "--branch" in sys.argv:
        idx = sys.argv.index("--branch")
        if idx + 1 >= len(sys.argv):
            raise SystemExit(
                "--branch requires a branch name argument.\n"
                "Usage: agent_push.py [--dry-run] [--branch <name>]"
            )
        branch_name = sys.argv[idx + 1].strip()
        if not branch_name:
            raise SystemExit(
                "--branch value must not be empty.\n"
                "If calling from CI, ensure the variable is set."
            )

    print("Reading agent_config/...")
    config = read_config()

    print("\nPayload summary:")
    summarise_payload(config)

    payload = build_payload(config)

    if dry_run:
        print("\n  Dry run -- no changes pushed.")
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:2000])
        return

    # ── Resolve or create branch ──
    branch_id = None
    if branch_name:
        print("\nPreparing branch '{}'...".format(branch_name))
        print("  Enabling versioning (if not already enabled)...")
        api.patch_agent({"enable_versioning_if_not_enabled": True})

        branches = api.list_branches()
        existing = None
        for b in branches:
            if b.get("name") == branch_name:
                existing = b
                break

        if existing:
            branch_id = existing["id"]
            print("  Found existing branch: {}".format(branch_id))
        else:
            # Find Main branch and its latest version
            main_branch = None
            for b in branches:
                if b.get("name") == "Main":
                    main_branch = b
                    break
            if not main_branch:
                raise SystemExit("Could not find Main branch.")

            main_details = api.get_branch(main_branch["id"])
            versions = (main_details.get("most_recent_versions")
                        or main_details.get("versions", []))
            if not versions:
                raise SystemExit("Main branch has no versions.")

            parent_id = versions[0].get("id") or versions[0].get("version_id")
            if not parent_id:
                raise SystemExit(
                    "Cannot determine Main branch tip version ID.\n"
                    "Response: {}".format(json.dumps(versions[0])[:200]))

            print("  Creating from Main tip ({})...".format(parent_id[:20]))
            result = api.create_branch(parent_id, branch_name,
                                       "Created by agent_push.py")
            branch_id = result.get("created_branch_id")
            if not branch_id:
                raise SystemExit(
                    "Branch creation returned no ID.\n"
                    "Response: {}".format(json.dumps(result)[:500]))
            print("  Branch created: {}".format(branch_id))

    target = " (branch: {})".format(branch_name) if branch_name else ""
    print("\nPushing to ElevenLabs{}...".format(target))
    result = api.patch_agent(payload, branch_id=branch_id)
    print("  Agent '{}' updated successfully.".format(result.get("name", "?")))

    # Quick verification
    print("\nVerifying...")
    updated = api.get_agent(branch_id=branch_id)
    live_dc = api.extract_data_collection(updated)
    live_prompt = api.extract_prompt(updated)

    dc_match = live_dc == config["data_collection"]
    prompt_match = live_prompt.strip() == config["prompt"].strip()

    print("  Data collection fields match: {}".format(dc_match))
    print("  System prompt match:          {}".format(prompt_match))

    # Workflow verification
    workflow = config.get("workflow")
    if workflow:
        live_wf = api.extract_workflow(updated)
        wf_match = live_wf is not None
        print("  Workflow present:             {}".format(wf_match))
    else:
        wf_match = True

    # Tools verification
    tools = config.get("tools", [])
    if tools:
        live_tools = api.extract_tools(updated)
        tool_names = sorted(t.get("name", "") for t in tools)
        live_names = sorted(t.get("name", "") for t in live_tools)
        tools_match = tool_names == live_names
        print("  System tools match:           {}".format(tools_match))
    else:
        tools_match = True

    # Multi-voice verification
    voices = config.get("supported_voices", [])
    if voices:
        live_voices = api.extract_supported_voices(updated)
        voice_labels = sorted(v.get("label", "") for v in voices)
        live_labels = sorted(v.get("label", "") for v in live_voices)
        voices_match = voice_labels == live_labels
        print("  Multi-voice match:            {}".format(voices_match))
    else:
        voices_match = True

    all_match = dc_match and prompt_match and wf_match and tools_match and voices_match
    if all_match:
        print("\n  Live agent is in sync with agent_config/.")
    else:
        print("\n  Drift detected after push -- check the ElevenLabs dashboard.")
        if not dc_match:
            local_keys = set(config["data_collection"].keys())
            live_keys = set(live_dc.keys())
            added = live_keys - local_keys
            removed = local_keys - live_keys
            if added:
                print("    Unexpected live fields: {}".format(sorted(added)))
            if removed:
                print("    Missing live fields:    {}".format(sorted(removed)))
            for key in sorted(local_keys & live_keys):
                if config["data_collection"][key] != live_dc.get(key):
                    print("    Definition differs:     {}".format(key))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
agent_push.py — Push local agent_config/ to the ElevenLabs agent.

Reads system_prompt.md, data_collection.json, settings.json, and
(optionally) workflow.json + nodes/*/prompt.md from agent_config/
and PATCHes the live agent so it matches.

Usage:
  source .env && python3 scripts/agent_push.py
  source .env && python3 scripts/agent_push.py --dry-run
"""

import json
import os
import sys

# Allow importing the shared helpers from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _elevenlabs as api

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(REPO_ROOT, "agent_config")


def read_config():
    """Read all three config files and return a structured dict."""
    prompt_path = os.path.join(CONFIG_DIR, "system_prompt.md")
    dc_path = os.path.join(CONFIG_DIR, "data_collection.json")
    settings_path = os.path.join(CONFIG_DIR, "settings.json")

    missing = [p for p in (prompt_path, dc_path, settings_path) if not os.path.exists(p)]
    if missing:
        raise SystemExit(
            "Missing config files:\n" + "\n".join(f"  {p}" for p in missing)
        )

    with open(prompt_path, encoding="utf-8") as f:
        prompt = f.read().strip()

    with open(dc_path, encoding="utf-8") as f:
        data_collection = json.load(f)

    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)

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
                fpath = os.path.join(CONFIG_DIR, rel)
                if not os.path.exists(fpath):
                    slug = api.node_slug(node)
                    print(f"  ⚠ Missing prompt file for node '{slug}': {rel}")
                    continue
                with open(fpath, encoding="utf-8") as f:
                    api.set_node_prompt(node, path, f.read().strip())

    return prompt, data_collection, settings, workflow


def build_payload(prompt: str, data_collection: dict, settings: dict,
                  workflow: dict = None) -> dict:
    """Build the PATCH payload from local config."""
    llm = settings.get("llm", {})
    voice = settings.get("voice", {})

    payload = {
        "name": settings.get("name"),
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": prompt,
                    "llm": llm.get("provider"),
                    "model": llm.get("model") or None,
                    "temperature": llm.get("temperature"),
                    "max_tokens": llm.get("max_tokens"),
                },
                "first_message": settings.get("first_message"),
                "language": settings.get("language"),
                "dynamic_variables": {
                    "dynamic_variable_placeholders": settings.get("dynamic_variables", {}),
                },
            },
            # Only include TTS fields that have explicit values —
            # the API may reject or misinterpret null for optional fields.
            "tts": {
                k: v for k, v in {
                    "voice_id": voice.get("voice_id"),
                    "model_id": voice.get("model_id"),
                    "stability": voice.get("stability"),
                    "similarity_boost": voice.get("similarity_boost"),
                    "style": voice.get("style"),
                    "speed": voice.get("speed"),
                    "optimize_streaming_latency": voice.get("optimize_streaming_latency"),
                }.items() if v is not None
            },
        },
        "platform_settings": {
            "data_collection": data_collection,
        },
    }

    if workflow:
        payload["workflow"] = workflow

    return payload


def summarise_payload(prompt, data_collection, settings, workflow=None):
    """Print a human-readable summary of what will be pushed."""
    llm = settings.get("llm", {})
    voice = settings.get("voice", {})

    print(f"  Name:           {settings.get('name')}")
    print(f"  Language:       {settings.get('language')}")
    print(f"  LLM:            {llm.get('provider')} (temp={llm.get('temperature')})")
    print(f"  Voice:          {voice.get('voice_id')} ({voice.get('model_id')})")
    print(f"  System prompt:  {len(prompt)} chars, ~{len(prompt.split())} words")
    print(f"  Data fields:    {list(data_collection.keys())}")
    dv = settings.get("dynamic_variables", {})
    ellip = "\u2026" if len(dv) > 5 else ""
    print(f"  Dyn variables:  {len(dv)} ({', '.join(sorted(dv)[:5])}{ellip})")
    first_msg = settings.get("first_message", "")[:60]
    print(f"  First message:  {first_msg}\u2026")
    if workflow:
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])
        print(f"  Workflow:       {len(nodes)} nodes, {len(edges)} edges")
    else:
        print(f"  Workflow:       none (single-agent mode)")


def main():
    dry_run = "--dry-run" in sys.argv

    print("Reading agent_config/...")
    prompt, data_collection, settings, workflow = read_config()

    print("\nPayload summary:")
    summarise_payload(prompt, data_collection, settings, workflow)

    payload = build_payload(prompt, data_collection, settings, workflow)

    if dry_run:
        print("\n🏜️  Dry run — no changes pushed.")
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:2000])
        return

    print("\nPushing to ElevenLabs...")
    result = api.patch_agent(payload)
    print(f"  ✓ Agent '{result.get('name', '?')}' updated successfully.")

    # Quick verification — compare normalized definitions, not just keys
    print("\nVerifying...")
    updated = api.get_agent()
    live_dc = api.extract_data_collection(updated)
    live_prompt = api.extract_prompt(updated)

    dc_match = live_dc == data_collection
    prompt_match = live_prompt.strip() == prompt.strip()

    print(f"  Data collection fields match: {dc_match}")
    print(f"  System prompt match:          {prompt_match}")

    # Workflow verification
    if workflow:
        live_wf = api.extract_workflow(updated)
        wf_match = live_wf is not None
        print(f"  Workflow present:             {wf_match}")
    else:
        wf_match = True

    if dc_match and prompt_match and wf_match:
        print("\n✅ Live agent is in sync with agent_config/.")
    else:
        print("\n⚠️  Drift detected after push — check the ElevenLabs dashboard.")
        if not dc_match:
            local_keys = set(data_collection.keys())
            live_keys = set(live_dc.keys())
            added = live_keys - local_keys
            removed = local_keys - live_keys
            if added:
                print(f"    Unexpected live fields: {sorted(added)}")
            if removed:
                print(f"    Missing live fields:    {sorted(removed)}")
            for key in sorted(local_keys & live_keys):
                if data_collection[key] != live_dc.get(key):
                    print(f"    Definition differs:     {key}")


if __name__ == "__main__":
    main()

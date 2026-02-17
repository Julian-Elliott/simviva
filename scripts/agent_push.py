#!/usr/bin/env python3
"""
agent_push.py — Push local agent_config/ to the ElevenLabs agent.

Reads system_prompt.md, data_collection.json, and settings.json from
agent_config/ and PATCHes the live agent so it matches.

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

    with open(prompt_path) as f:
        prompt = f.read().strip()

    with open(dc_path) as f:
        data_collection = json.load(f)

    with open(settings_path) as f:
        settings = json.load(f)

    return prompt, data_collection, settings


def build_payload(prompt: str, data_collection: dict, settings: dict) -> dict:
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
            },
            "tts": {
                "voice_id": voice.get("voice_id"),
                "model_id": voice.get("model_id"),
                "stability": voice.get("stability"),
                "similarity_boost": voice.get("similarity_boost"),
                "speed": voice.get("speed"),
                "optimize_streaming_latency": voice.get("optimize_streaming_latency"),
            },
        },
        "platform_settings": {
            "data_collection": data_collection,
        },
    }

    # Include style only if explicitly set (null/None means omit)
    if voice.get("style") is not None:
        payload["conversation_config"]["tts"]["style"] = voice["style"]

    return payload


def summarise_payload(prompt, data_collection, settings):
    """Print a human-readable summary of what will be pushed."""
    llm = settings.get("llm", {})
    voice = settings.get("voice", {})

    print(f"  Name:           {settings.get('name')}")
    print(f"  Language:       {settings.get('language')}")
    print(f"  LLM:            {llm.get('provider')} (temp={llm.get('temperature')})")
    print(f"  Voice:          {voice.get('voice_id')} ({voice.get('model_id')})")
    print(f"  System prompt:  {len(prompt)} chars, ~{len(prompt.split())} words")
    print(f"  Data fields:    {list(data_collection.keys())}")
    print(f"  First message:  {settings.get('first_message', '')[:60]}…")


def main():
    dry_run = "--dry-run" in sys.argv

    print("Reading agent_config/...")
    prompt, data_collection, settings = read_config()

    print("\nPayload summary:")
    summarise_payload(prompt, data_collection, settings)

    payload = build_payload(prompt, data_collection, settings)

    if dry_run:
        print("\n🏜️  Dry run — no changes pushed.")
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:2000])
        return

    print("\nPushing to ElevenLabs...")
    result = api.patch_agent(payload)
    print(f"  ✓ Agent '{result.get('name', '?')}' updated successfully.")

    # Quick verification
    print("\nVerifying...")
    updated = api.get_agent()
    live_dc = api.extract_data_collection(updated)
    live_prompt = api.extract_prompt(updated)

    dc_match = set(live_dc.keys()) == set(data_collection.keys())
    prompt_match = live_prompt.strip() == prompt.strip()

    print(f"  Data collection fields match: {dc_match}")
    print(f"  System prompt match:          {prompt_match}")

    if dc_match and prompt_match:
        print("\n✅ Live agent is in sync with agent_config/.")
    else:
        print("\n⚠️  Drift detected after push — check the ElevenLabs dashboard.")
        if not dc_match:
            print(f"    Expected fields: {sorted(data_collection.keys())}")
            print(f"    Live fields:     {sorted(live_dc.keys())}")


if __name__ == "__main__":
    main()

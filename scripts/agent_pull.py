#!/usr/bin/env python3
"""
agent_pull.py — Pull live ElevenLabs agent config into agent_config/.

Fetches the current agent state and overwrites the local config files so
they reflect reality.  Use --diff to compare without changing anything.

Usage:
  source .env && python3 scripts/agent_pull.py          # overwrite local files
  source .env && python3 scripts/agent_pull.py --diff    # diff only, no writes
"""

import difflib
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _elevenlabs as api

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(REPO_ROOT, "agent_config")
HISTORY_DIR = os.path.join(CONFIG_DIR, "history")


# ── Helpers ──

def read_local_file(path: str) -> str:
    """Read a local file, returning '' if it doesn't exist."""
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read()


def coloured_diff(local_lines: list[str], remote_lines: list[str],
                  local_label: str, remote_label: str) -> str:
    """Return a unified diff string, coloured for terminal output."""
    diff = difflib.unified_diff(
        local_lines, remote_lines,
        fromfile=f"local ({local_label})",
        tofile=f"live  ({remote_label})",
        lineterm="",
    )
    lines = []
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            lines.append(f"\033[1m{line}\033[0m")  # bold
        elif line.startswith("+"):
            lines.append(f"\033[32m{line}\033[0m")  # green
        elif line.startswith("-"):
            lines.append(f"\033[31m{line}\033[0m")  # red
        elif line.startswith("@@"):
            lines.append(f"\033[36m{line}\033[0m")  # cyan
        else:
            lines.append(line)
    return "\n".join(lines)


# ── Core ──

def pull_to_local(agent: dict):
    """Overwrite local config files with the live agent state."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # System prompt
    prompt = api.extract_prompt(agent)
    prompt_path = os.path.join(CONFIG_DIR, "system_prompt.md")
    with open(prompt_path, "w") as f:
        f.write(prompt)
        if not prompt.endswith("\n"):
            f.write("\n")
    print(f"  ✓ system_prompt.md  ({len(prompt)} chars)")

    # Data collection
    dc = api.extract_data_collection(agent)
    dc_path = os.path.join(CONFIG_DIR, "data_collection.json")
    with open(dc_path, "w") as f:
        json.dump(dc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  ✓ data_collection.json  ({len(dc)} fields)")

    # Settings
    settings = {
        "name": agent.get("name", ""),
        "language": api.extract_language(agent),
        "llm": api.extract_llm(agent),
        "voice": api.extract_voice(agent),
        "first_message": api.extract_first_message(agent),
    }
    settings_path = os.path.join(CONFIG_DIR, "settings.json")
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  ✓ settings.json")

    # Timestamped history copy (gitignored)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    history_path = os.path.join(HISTORY_DIR, f"{ts}.json")
    with open(history_path, "w") as f:
        json.dump(agent, f, indent=2, ensure_ascii=False)
    print(f"  ✓ history/{ts}.json")


def diff_against_local(agent: dict):
    """Compare the live agent against local config files and print diffs."""
    any_diff = False

    # 1. System prompt
    local_prompt = read_local_file(os.path.join(CONFIG_DIR, "system_prompt.md")).strip()
    live_prompt = api.extract_prompt(agent).strip()

    if local_prompt != live_prompt:
        any_diff = True
        print("\n── system_prompt.md ──")
        print(coloured_diff(
            local_prompt.splitlines(), live_prompt.splitlines(),
            "system_prompt.md", "ElevenLabs",
        ))
    else:
        print("  system_prompt.md    ✓ in sync")

    # 2. Data collection
    local_dc_text = read_local_file(os.path.join(CONFIG_DIR, "data_collection.json")).strip()
    live_dc = api.extract_data_collection(agent)
    live_dc_text = json.dumps(live_dc, indent=2, ensure_ascii=False)

    if local_dc_text != live_dc_text:
        any_diff = True
        print("\n── data_collection.json ──")
        print(coloured_diff(
            local_dc_text.splitlines(), live_dc_text.splitlines(),
            "data_collection.json", "ElevenLabs",
        ))
    else:
        print("  data_collection.json ✓ in sync")

    # 3. Settings
    local_settings_text = read_local_file(os.path.join(CONFIG_DIR, "settings.json")).strip()
    live_settings = {
        "name": agent.get("name", ""),
        "language": api.extract_language(agent),
        "llm": api.extract_llm(agent),
        "voice": api.extract_voice(agent),
        "first_message": api.extract_first_message(agent),
    }
    live_settings_text = json.dumps(live_settings, indent=2, ensure_ascii=False)

    if local_settings_text != live_settings_text:
        any_diff = True
        print("\n── settings.json ──")
        print(coloured_diff(
            local_settings_text.splitlines(), live_settings_text.splitlines(),
            "settings.json", "ElevenLabs",
        ))
    else:
        print("  settings.json       ✓ in sync")

    if any_diff:
        print("\n⚠️  Drift detected. Run without --diff to pull, or fix locally and push.")
    else:
        print("\n✅ Local config matches the live agent.")


def main():
    diff_only = "--diff" in sys.argv

    print("Fetching agent config from ElevenLabs...")
    agent = api.get_agent()
    print(f"  Agent: {agent.get('name', '?')}\n")

    if diff_only:
        print("Comparing local config against live agent...\n")
        diff_against_local(agent)
    else:
        print("Writing live config to agent_config/...")
        pull_to_local(agent)
        print(f"\n✅ Local config updated from live agent.")
        print("   Tip: git diff agent_config/ to see what changed.")


if __name__ == "__main__":
    main()

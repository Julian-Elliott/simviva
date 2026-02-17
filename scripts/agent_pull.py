#!/usr/bin/env python3
"""
agent_pull.py — Pull live ElevenLabs agent config into agent_config/.

Fetches the current agent state and overwrites the local config files so
they reflect reality.  Use --diff to compare without changing anything.

Usage:
  source .env && python3 scripts/agent_pull.py          # overwrite local files
  source .env && python3 scripts/agent_pull.py --diff    # diff only, no writes
"""

import copy
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
    with open(path, encoding="utf-8") as f:
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
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)
        if not prompt.endswith("\n"):
            f.write("\n")
    print(f"  ✓ system_prompt.md  ({len(prompt)} chars)")

    # Data collection
    dc = api.extract_data_collection(agent)
    dc_path = os.path.join(CONFIG_DIR, "data_collection.json")
    with open(dc_path, "w", encoding="utf-8") as f:
        json.dump(dc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  ✓ data_collection.json  ({len(dc)} fields)")

    # Settings
    settings = {
        "name": agent.get("name", ""),
        "language": api.extract_language(agent),
        "llm": api.extract_llm(agent),
        "voice": api.extract_voice(agent),
        "dynamic_variables": api.extract_dynamic_variables(agent),
        "first_message": api.extract_first_message(agent),
    }
    settings_path = os.path.join(CONFIG_DIR, "settings.json")
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    dv_count = len(settings["dynamic_variables"])
    print(f"  ✓ settings.json  ({dv_count} dynamic variables)")

    # Timestamped history copy (gitignored)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    history_path = os.path.join(HISTORY_DIR, f"{ts}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(agent, f, indent=2, ensure_ascii=False)
    print(f"  ✓ history/{ts}.json")

    # Workflow (present only when the agent uses ElevenLabs Workflows)
    workflow = api.extract_workflow(agent)
    if workflow:
        wf = copy.deepcopy(workflow)
        nodes_dir = os.path.join(CONFIG_DIR, "nodes")
        node_count = 0
        prompt_count = 0
        for node in wf.get("nodes", []):
            node_count += 1
            slug = api.node_slug(node)
            node_prompt, path = api.find_node_prompt(node)
            if node_prompt and path:
                prompt_count += 1
                node_dir = os.path.join(nodes_dir, slug)
                os.makedirs(node_dir, exist_ok=True)
                pfile = os.path.join(node_dir, "prompt.md")
                with open(pfile, "w", encoding="utf-8") as f:
                    f.write(node_prompt)
                    if not node_prompt.endswith("\n"):
                        f.write("\n")
                print(f"  ✓ nodes/{slug}/prompt.md  ({len(node_prompt)} chars)")
                # Replace prompt in JSON with a file marker
                api.set_node_prompt(
                    node, path,
                    f"{api.PROMPT_FILE_PREFIX}nodes/{slug}/prompt.md",
                )

        wf_path = os.path.join(CONFIG_DIR, "workflow.json")
        with open(wf_path, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  ✓ workflow.json  ({node_count} nodes, {prompt_count} prompt files)")
    else:
        print("  · No workflow (single-agent mode)")


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
    local_dc_raw = read_local_file(os.path.join(CONFIG_DIR, "data_collection.json")).strip()
    local_dc = json.loads(local_dc_raw) if local_dc_raw else {}
    live_dc = api.extract_data_collection(agent)
    local_dc_text = json.dumps(local_dc, indent=2, sort_keys=True, ensure_ascii=False)
    live_dc_text = json.dumps(live_dc, indent=2, sort_keys=True, ensure_ascii=False)

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
    local_settings_raw = read_local_file(os.path.join(CONFIG_DIR, "settings.json")).strip()
    local_settings = json.loads(local_settings_raw) if local_settings_raw else {}
    live_settings = {
        "name": agent.get("name", ""),
        "language": api.extract_language(agent),
        "llm": api.extract_llm(agent),
        "voice": api.extract_voice(agent),
        "dynamic_variables": api.extract_dynamic_variables(agent),
        "first_message": api.extract_first_message(agent),
    }
    local_settings_text = json.dumps(local_settings, indent=2, sort_keys=True, ensure_ascii=False)
    live_settings_text = json.dumps(live_settings, indent=2, sort_keys=True, ensure_ascii=False)

    if local_settings_text != live_settings_text:
        any_diff = True
        print("\n── settings.json ──")
        print(coloured_diff(
            local_settings_text.splitlines(), live_settings_text.splitlines(),
            "settings.json", "ElevenLabs",
        ))
    else:
        print("  settings.json       ✓ in sync")

    # 4. Workflow
    live_wf = api.extract_workflow(agent)
    local_wf_raw = read_local_file(os.path.join(CONFIG_DIR, "workflow.json")).strip()

    if live_wf and local_wf_raw:
        # Reassemble local workflow: inject prompt files back into JSON
        local_wf = json.loads(local_wf_raw)
        for node in local_wf.get("nodes", []):
            node_prompt, path = api.find_node_prompt(node)
            if isinstance(node_prompt, str) and node_prompt.startswith(api.PROMPT_FILE_PREFIX):
                rel = node_prompt[len(api.PROMPT_FILE_PREFIX):]
                content = read_local_file(os.path.join(CONFIG_DIR, rel)).strip()
                if content:
                    api.set_node_prompt(node, path, content)

        local_text = json.dumps(local_wf, indent=2, sort_keys=True, ensure_ascii=False)
        live_text = json.dumps(live_wf, indent=2, sort_keys=True, ensure_ascii=False)

        if local_text != live_text:
            any_diff = True
            print("\n── workflow.json ──")
            print(coloured_diff(
                local_text.splitlines(), live_text.splitlines(),
                "workflow.json (assembled)", "ElevenLabs",
            ))
        else:
            print("  workflow.json        ✓ in sync")
    elif live_wf and not local_wf_raw:
        any_diff = True
        print("  workflow.json        ⚠ live workflow exists but no local file")
    elif not live_wf and local_wf_raw:
        any_diff = True
        print("  workflow.json        ⚠ local file exists but no live workflow")
    else:
        print("  workflow              · no workflow (single-agent mode)")

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

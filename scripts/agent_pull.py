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
import shutil
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
    print("  system_prompt.md  ({} chars)".format(len(prompt)))

    # Data collection
    dc = api.extract_data_collection(agent)
    dc_path = os.path.join(CONFIG_DIR, "data_collection.json")
    with open(dc_path, "w", encoding="utf-8") as f:
        json.dump(dc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("  data_collection.json  ({} fields)".format(len(dc)))

    # Settings (includes ASR)
    asr = api.extract_asr(agent)
    settings = {
        "name": agent.get("name", ""),
        "language": api.extract_language(agent),
        "llm": api.extract_llm(agent),
        "voice": api.extract_voice(agent),
    }
    if asr:
        settings["asr"] = asr
    settings["dynamic_variables"] = api.extract_dynamic_variables(agent)
    settings["first_message"] = api.extract_first_message(agent)

    settings_path = os.path.join(CONFIG_DIR, "settings.json")
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    dv_count = len(settings["dynamic_variables"])
    kw_count = len(asr.get("keywords", []))
    print("  settings.json  ({} dynamic variables, {} ASR keywords)".format(dv_count, kw_count))

    # Conversation flow (turn + conversation settings)
    turn = api.extract_turn(agent)
    conv = api.extract_conversation(agent)
    if turn or conv:
        cf = {}
        if turn:
            cf["turn"] = turn
        if conv:
            cf["conversation"] = conv
        cf_path = os.path.join(CONFIG_DIR, "conversation_flow.json")
        with open(cf_path, "w", encoding="utf-8") as f:
            json.dump(cf, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("  conversation_flow.json  (timeout={}, eagerness={})".format(
            turn.get("turn_timeout", "?"), turn.get("turn_eagerness", "?")))

    # Tools
    tools = api.extract_tools(agent)
    if tools:
        tools_path = os.path.join(CONFIG_DIR, "tools.json")
        with open(tools_path, "w", encoding="utf-8") as f:
            json.dump(tools, f, indent=2, ensure_ascii=False)
            f.write("\n")
        names = [t.get("name", "?") for t in tools]
        print("  tools.json  ({})".format(names))

    # Supported voices
    voices = api.extract_supported_voices(agent)
    if voices:
        voices_path = os.path.join(CONFIG_DIR, "supported_voices.json")
        with open(voices_path, "w", encoding="utf-8") as f:
            json.dump(voices, f, indent=2, ensure_ascii=False)
            f.write("\n")
        labels = [v.get("label", "?") for v in voices]
        print("  supported_voices.json  ({})".format(labels))

    # Evaluation criteria
    criteria = api.extract_evaluation_criteria(agent)
    if criteria:
        eval_path = os.path.join(CONFIG_DIR, "evaluation_criteria.json")
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(criteria, f, indent=2, ensure_ascii=False)
            f.write("\n")
        names = [c.get("name", "?") for c in criteria]
        print("  evaluation_criteria.json  ({})".format(names))

    # Pronunciation dictionary locators
    locators = api.extract_pronunciation_locators(agent)
    if locators:
        # Store only the first locator (we only use one dictionary)
        loc = locators[0] if locators else {}
        loc_path = os.path.join(CONFIG_DIR, "pronunciation_locator.json")
        with open(loc_path, "w", encoding="utf-8") as f:
            json.dump(loc, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("  pronunciation_locator.json  (id={})".format(
            loc.get("pronunciation_dictionary_id", "none")))

    # Timestamped history copy (gitignored)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    history_path = os.path.join(HISTORY_DIR, "{}.json".format(ts))
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(agent, f, indent=2, ensure_ascii=False)
    print("  history/{}.json".format(ts))

    # Workflow (present only when the agent uses ElevenLabs Workflows)
    workflow = api.extract_workflow(agent)
    if workflow:
        wf = copy.deepcopy(workflow)
        nodes_dir = os.path.join(CONFIG_DIR, "nodes")

        # Build the set of slugs we expect to write so we can prune stale dirs
        expected_slugs = set()
        for node in wf.get("nodes", []):
            expected_slugs.add(api.node_slug(node))

        # Remove node directories that no longer exist in the live workflow
        if os.path.isdir(nodes_dir):
            for entry in os.listdir(nodes_dir):
                entry_path = os.path.join(nodes_dir, entry)
                if os.path.isdir(entry_path) and entry not in expected_slugs:
                    shutil.rmtree(entry_path)
                    print("  removed stale nodes/{}/".format(entry))

        node_count = 0
        prompt_count = 0
        for node in wf.get("nodes", []):
            node_count += 1
            slug = api.node_slug(node)
            node_prompt, path = api.find_node_prompt(node)
            if node_prompt and path:
                prompt_count += 1
                node_dir = os.path.join(nodes_dir, slug)
                try:
                    api.safe_resolve(CONFIG_DIR, os.path.join("nodes", slug))
                except ValueError as e:
                    raise SystemExit("Refusing to write: {}".format(e))
                os.makedirs(node_dir, exist_ok=True)
                pfile = os.path.join(node_dir, "prompt.md")
                with open(pfile, "w", encoding="utf-8") as f:
                    f.write(node_prompt)
                    if not node_prompt.endswith("\n"):
                        f.write("\n")
                print("  nodes/{}/prompt.md  ({} chars)".format(slug, len(node_prompt)))
                # Replace prompt in JSON with a file marker
                api.set_node_prompt(
                    node, path,
                    "{}nodes/{}/prompt.md".format(api.PROMPT_FILE_PREFIX, slug),
                )

        wf_path = os.path.join(CONFIG_DIR, "workflow.json")
        with open(wf_path, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("  workflow.json  ({} nodes, {} prompt files)".format(node_count, prompt_count))
    else:
        # No live workflow — clean up any stale local workflow artefacts
        wf_path = os.path.join(CONFIG_DIR, "workflow.json")
        nodes_dir = os.path.join(CONFIG_DIR, "nodes")
        removed = []
        if os.path.exists(wf_path):
            os.remove(wf_path)
            removed.append("workflow.json")
        if os.path.isdir(nodes_dir):
            shutil.rmtree(nodes_dir)
            removed.append("nodes/")
        if removed:
            print("  No workflow (single-agent mode) — removed stale {}".format(
                ", ".join(removed)))
        else:
            print("  No workflow (single-agent mode)")


def _diff_json(local_obj, live_obj, label: str, any_diff_ref: list) -> None:
    """Compare two JSON-serialisable objects and print a diff if different."""
    local_text = json.dumps(local_obj, indent=2, sort_keys=True, ensure_ascii=False)
    live_text = json.dumps(live_obj, indent=2, sort_keys=True, ensure_ascii=False)
    if local_text != live_text:
        any_diff_ref.append(True)
        print("\n-- {} --".format(label))
        print(coloured_diff(
            local_text.splitlines(), live_text.splitlines(),
            label, "ElevenLabs",
        ))
    else:
        pad = max(0, 26 - len(label))
        print("  {}{}in sync".format(label, " " * pad))


def diff_against_local(agent: dict):
    """Compare the live agent against local config files and print diffs."""
    any_diff = []

    # 1. System prompt
    local_prompt = read_local_file(os.path.join(CONFIG_DIR, "system_prompt.md")).strip()
    live_prompt = api.extract_prompt(agent).strip()

    if local_prompt != live_prompt:
        any_diff.append(True)
        print("\n-- system_prompt.md --")
        print(coloured_diff(
            local_prompt.splitlines(), live_prompt.splitlines(),
            "system_prompt.md", "ElevenLabs",
        ))
    else:
        print("  system_prompt.md        in sync")

    # 2. Data collection
    local_dc_raw = read_local_file(os.path.join(CONFIG_DIR, "data_collection.json")).strip()
    local_dc = json.loads(local_dc_raw) if local_dc_raw else {}
    live_dc = api.extract_data_collection(agent)
    _diff_json(local_dc, live_dc, "data_collection.json", any_diff)

    # 3. Settings (reconstruct what pull would write)
    local_settings_raw = read_local_file(os.path.join(CONFIG_DIR, "settings.json")).strip()
    local_settings = json.loads(local_settings_raw) if local_settings_raw else {}
    asr = api.extract_asr(agent)
    live_settings = {
        "name": agent.get("name", ""),
        "language": api.extract_language(agent),
        "llm": api.extract_llm(agent),
        "voice": api.extract_voice(agent),
    }
    if asr:
        live_settings["asr"] = asr
    live_settings["dynamic_variables"] = api.extract_dynamic_variables(agent)
    live_settings["first_message"] = api.extract_first_message(agent)
    _diff_json(local_settings, live_settings, "settings.json", any_diff)

    # 4. Conversation flow
    local_cf_raw = read_local_file(os.path.join(CONFIG_DIR, "conversation_flow.json")).strip()
    local_cf = json.loads(local_cf_raw) if local_cf_raw else {}
    turn = api.extract_turn(agent)
    conv = api.extract_conversation(agent)
    live_cf = {}
    if turn:
        live_cf["turn"] = turn
    if conv:
        live_cf["conversation"] = conv
    if local_cf or live_cf:
        _diff_json(local_cf, live_cf, "conversation_flow.json", any_diff)

    # 5. Tools
    local_tools_raw = read_local_file(os.path.join(CONFIG_DIR, "tools.json")).strip()
    local_tools = json.loads(local_tools_raw) if local_tools_raw else []
    live_tools = api.extract_tools(agent)
    if local_tools or live_tools:
        _diff_json(local_tools, live_tools, "tools.json", any_diff)

    # 6. Supported voices
    local_voices_raw = read_local_file(os.path.join(CONFIG_DIR, "supported_voices.json")).strip()
    local_voices = json.loads(local_voices_raw) if local_voices_raw else []
    live_voices = api.extract_supported_voices(agent)
    if local_voices or live_voices:
        _diff_json(local_voices, live_voices, "supported_voices.json", any_diff)

    # 7. Evaluation criteria
    local_eval_raw = read_local_file(os.path.join(CONFIG_DIR, "evaluation_criteria.json")).strip()
    local_eval = json.loads(local_eval_raw) if local_eval_raw else []
    live_eval = api.extract_evaluation_criteria(agent)
    if local_eval or live_eval:
        _diff_json(local_eval, live_eval, "evaluation_criteria.json", any_diff)

    # 8. Pronunciation locator
    local_pron_raw = read_local_file(os.path.join(CONFIG_DIR, "pronunciation_locator.json")).strip()
    local_pron = json.loads(local_pron_raw) if local_pron_raw else {}
    live_locators = api.extract_pronunciation_locators(agent)
    live_pron = live_locators[0] if live_locators else {}
    # Only compare if either side has a valid dictionary ID
    local_id = local_pron.get("pronunciation_dictionary_id")
    live_id = live_pron.get("pronunciation_dictionary_id")
    if local_id or live_id:
        _diff_json(local_pron, live_pron, "pronunciation_locator.json", any_diff)

    # 9. Workflow
    live_wf = api.extract_workflow(agent)
    local_wf_raw = read_local_file(os.path.join(CONFIG_DIR, "workflow.json")).strip()

    if live_wf and local_wf_raw:
        # Reassemble local workflow: inject prompt files back into JSON
        local_wf = json.loads(local_wf_raw)
        for node in local_wf.get("nodes", []):
            node_prompt, path = api.find_node_prompt(node)
            if isinstance(node_prompt, str) and node_prompt.startswith(api.PROMPT_FILE_PREFIX):
                rel = node_prompt[len(api.PROMPT_FILE_PREFIX):]
                try:
                    safe_path = api.safe_resolve(CONFIG_DIR, rel)
                except ValueError as e:
                    print("  Skipping unsafe marker: {}".format(e))
                    continue
                content = read_local_file(safe_path).strip()
                if content:
                    api.set_node_prompt(node, path, content)

        _diff_json(local_wf, live_wf, "workflow.json", any_diff)
    elif live_wf and not local_wf_raw:
        any_diff.append(True)
        print("  workflow.json            live workflow exists but no local file")
    elif not live_wf and local_wf_raw:
        any_diff.append(True)
        print("  workflow.json            local file exists but no live workflow")
    else:
        print("  workflow                 no workflow (single-agent mode)")

    if any_diff:
        print("\n  Drift detected. Run without --diff to pull, or fix locally and push.")
    else:
        print("\n  Local config matches the live agent.")


def main():
    diff_only = "--diff" in sys.argv

    print("Fetching agent config from ElevenLabs...")
    agent = api.get_agent()
    print("  Agent: {}\n".format(agent.get("name", "?")))

    if diff_only:
        print("Comparing local config against live agent...\n")
        diff_against_local(agent)
    else:
        print("Writing live config to agent_config/...")
        pull_to_local(agent)
        print("\n  Local config updated from live agent.")
        print("   Tip: git diff agent_config/ to see what changed.")


if __name__ == "__main__":
    main()

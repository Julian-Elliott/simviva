#!/usr/bin/env python3
"""
update_agent.py — Patch the ElevenLabs agent to align with the new data model.

Changes:
  1. System prompt: adds {{scenario_X_scoring}} variable references
  2. Data collection: updates candidate_grade to use RCoA 4-point scale
  3. Adds key_facts_covered and key_facts_missed data collection fields

Usage:
  source .env && python3 scripts/update_agent.py
"""

import json
import os
import urllib.error
import urllib.request

API_KEY = os.environ["ELEVENLABS_API_KEY"]

AGENT_ID = os.environ.get("ELEVENLABS_AGENT_ID", "").strip()
if not AGENT_ID:
    raise SystemExit(
        "Error: ELEVENLABS_AGENT_ID is not set.\n"
        "Run:  source .env && python3 scripts/update_agent.py\n"
        "Or set the variable to the target agent ID before running."
    )

BASE_URL = f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}"


def get_agent():
    req = urllib.request.Request(BASE_URL, headers={"xi-api-key": API_KEY})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(
            f"GET {BASE_URL} failed ({e.code} {e.reason})\n{body}"
        ) from None
    except urllib.error.URLError as e:
        raise SystemExit(f"GET {BASE_URL} — network error: {e.reason}") from None
    return json.loads(resp.read())


def patch_agent(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"xi-api-key": API_KEY, "Content-Type": "application/json"},
        method="PATCH",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(
            f"PATCH {BASE_URL} failed ({e.code} {e.reason})\n{body}"
        ) from None
    except urllib.error.URLError as e:
        raise SystemExit(f"PATCH {BASE_URL} — network error: {e.reason}") from None
    return json.loads(resp.read())


def main():
    print("Fetching current agent config...")
    agent = get_agent()
    conv = agent["conversation_config"]
    prompt_obj = conv["agent"]["prompt"]
    old_prompt = prompt_obj["prompt"]

    # ── 1. Inject scoring guidance blocks into the system prompt ──
    scoring_block = """
## SCORING GUIDANCE (SimViva Session Grade)

Use the scenario-specific scoring rubric below when assessing the candidate.

### Dr Whitmore's Scenario Scoring:
{{scenario_1_scoring}}

### Dr Harris's Scenario Scoring:
{{scenario_2_scoring}}

After the viva, grade the candidate's OVERALL session on this 4-point scale:
- 4 = Pass+ (exceeds the expected standard)
- 3 = Pass (meets the expected standard)
- 2 = Borderline (approaches but does not meet the standard)
- 1 = Fail (significantly below the expected standard)

Note: The real RCoA SOE uses per-question marks (0/1/2) across 12 questions.
SimViva covers only 2 questions, so this holistic grade is a formative estimate,
not a real exam score.
"""

    # Check if scoring block is already present
    if "{{scenario_1_scoring}}" in old_prompt:
        print("  Scoring block already present in system prompt — skipping.")
        new_prompt = old_prompt
    else:
        # Insert before the EXAMINER CONDUCT section
        marker = "## EXAMINER CONDUCT"
        if marker in old_prompt:
            new_prompt = old_prompt.replace(marker, scoring_block + "\n" + marker)
            print("  ✓ Injected scoring guidance block into system prompt.")
        else:
            # Fallback: append at end
            new_prompt = old_prompt + "\n" + scoring_block
            print("  ✓ Appended scoring guidance block to system prompt.")

    # ── 2. Update data_collection to use RCoA scale ──
    new_data_collection = {
        "candidate_grade": {
            "type": "string",
            "description": (
                "You are the chief examiner. Based on the ENTIRE conversation and the "
                "SCORING GUIDANCE provided for each scenario, give the candidate a holistic "
                "session grade on the SimViva 4-point scale. Output ONLY the number first "
                "(4, 3, 2, or 1), then a dash, then one sentence justification.\n"
                "4 = Pass+ (exceeds expected standard — structured answers, depth, anticipated follow-ups)\n"
                "3 = Pass (meets expected standard — correct core knowledge, minor gaps only)\n"
                "2 = Borderline (approaches but does not meet — partial knowledge, significant gaps, needed rescue)\n"
                "1 = Fail (significantly below — major errors, unable to answer core questions, unsafe)\n"
                "Example: '3 — Candidate demonstrated adequate knowledge of propofol pharmacology "
                "with correct mechanism and dosing but lacked depth on context-sensitive half-time.'"
            ),
        },
        "topic_1_summary": {
            "type": "string",
            "description": (
                "Summarise the candidate's performance during Dr Whitmore's section. "
                "Reference specific key facts they covered and missed from the scenario's "
                "expected points. Did they need rescue questions? 2-3 sentences."
            ),
        },
        "topic_2_summary": {
            "type": "string",
            "description": (
                "Summarise the candidate's performance during Dr Harris's section. "
                "Reference specific key facts they covered and missed from the scenario's "
                "expected points. Did they need rescue questions? 2-3 sentences."
            ),
        },
        "key_facts_covered": {
            "type": "string",
            "description": (
                "List the key clinical facts the candidate correctly stated across BOTH "
                "scenarios. Use semicolons to separate each fact. Only include facts from "
                "the scenario's expected points list that the candidate demonstrably covered."
            ),
        },
        "key_facts_missed": {
            "type": "string",
            "description": (
                "List the key clinical facts the candidate FAILED to mention or got wrong "
                "across BOTH scenarios. Use semicolons to separate. Only include facts from "
                "the scenario's expected points that were clearly missed or incorrect."
            ),
        },
        "areas_for_improvement": {
            "type": "string",
            "description": (
                "Provide 2-3 specific clinical topics for revision. Identify moments where "
                "the candidate hesitated, gave incomplete answers, or missed expected points. "
                "Format: '1. [Topic] — [reason]'. Always provide at least two items."
            ),
        },
    }

    # ── 3. Build PATCH payload ──
    patch = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": new_prompt,
                }
            }
        },
        "platform_settings": {
            "data_collection": new_data_collection,
        },
    }

    print("\nPatching agent...")
    result = patch_agent(patch)
    print(f"  ✓ Agent '{result.get('name', '?')}' updated successfully.")

    # Verify
    print("\nVerifying changes...")
    updated = get_agent()
    dc = updated.get("platform_settings", {}).get("data_collection", {})
    print(f"  Data collection fields: {list(dc.keys())}")
    sp = updated["conversation_config"]["agent"]["prompt"]["prompt"]
    print(f"  System prompt contains scoring block: {'{{scenario_1_scoring}}' in sp}")
    print("\n✅ Agent aligned with new data model.")


if __name__ == "__main__":
    main()

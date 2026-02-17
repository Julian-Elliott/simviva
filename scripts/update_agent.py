#!/usr/bin/env python3
"""
update_agent.py — Patch the ElevenLabs agent to align with the new data model.

Changes:
  1. System prompt: adds {{scenario_X_scoring}} variable references
  2. Data collection: per-question marks (question_1_mark, question_2_mark) on RCoA 0/1/2 scale
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
## SCORING GUIDANCE (RCoA Per-Question Marking)

Use the scenario-specific scoring rubric below when assessing the candidate.
Mark each question INDEPENDENTLY on the official RCoA 3-point scale:
- 2 = Pass (meets or exceeds the expected standard)
- 1 = Borderline (approaches but does not reliably meet the standard)
- 0 = Fail (significantly below the expected standard)

### Dr Whitmore's Scenario Scoring:
{{scenario_1_scoring}}

### Dr Harris's Scenario Scoring:
{{scenario_2_scoring}}

After the viva, assign a SEPARATE mark (0, 1, or 2) for each question.
Do NOT average them — each question is marked independently, exactly as
in the real Primary FRCA SOE.
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
        "question_1_mark": {
            "type": "string",
            "description": (
                "You are the chief examiner. Based on the candidate's performance during "
                "Dr Whitmore's scenario and the SCORING GUIDANCE for that scenario, assign "
                "a mark on the RCoA per-question scale. Output ONLY the number first "
                "(0, 1, or 2), then a dash, then one sentence justification.\n"
                "2 = Pass (meets or exceeds expected standard — correct core knowledge, "
                "structured answer, good depth)\n"
                "1 = Borderline (approaches but does not reliably meet the standard — "
                "partial knowledge, significant gaps, needed rescue)\n"
                "0 = Fail (significantly below — major errors, unable to answer core "
                "questions, unsafe statements)\n"
                "Example: '2 — Candidate demonstrated clear understanding of propofol "
                "pharmacology with correct mechanism, dosing, and context-sensitive half-time.'"
            ),
        },
        "question_2_mark": {
            "type": "string",
            "description": (
                "You are the chief examiner. Based on the candidate's performance during "
                "Dr Harris's scenario and the SCORING GUIDANCE for that scenario, assign "
                "a mark on the RCoA per-question scale. Output ONLY the number first "
                "(0, 1, or 2), then a dash, then one sentence justification.\n"
                "2 = Pass (meets or exceeds expected standard — correct core knowledge, "
                "structured answer, good depth)\n"
                "1 = Borderline (approaches but does not reliably meet the standard — "
                "partial knowledge, significant gaps, needed rescue)\n"
                "0 = Fail (significantly below — major errors, unable to answer core "
                "questions, unsafe statements)\n"
                "Example: '1 — Candidate had partial knowledge of tracheostomy anatomy "
                "but could not describe the blood supply or innervation reliably.'"
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
    has_q1 = "question_1_mark" in dc
    has_q2 = "question_2_mark" in dc
    print(f"  Per-question marks: q1={has_q1}, q2={has_q2}")
    print("\n✅ Agent aligned with RCoA per-question marking.")


if __name__ == "__main__":
    main()

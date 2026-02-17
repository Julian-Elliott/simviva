#!/usr/bin/env python3
"""
build_scenarios.py — Compiles data/scenarios/*.json → webapp/scenarios.json

Bridges the rich Scenario schema (Layer 1) to the flat shape the ElevenLabs
agent and webapp currently consume.

Output shape per scenario:
{
  "id":        string,
  "domain":    string,
  "topicTagIds": string[],
  "caseId":    string | null,
  "slotType":  string,
  "caseOrder": number,
  "topic":     string,          ← first topicTagId, humanised
  "opening":   string,          ← stem
  "points":    string[],        ← all expectedKeyFacts across prompts
  "probes":    string[],        ← all prompt texts in tier order
  "facts":     string[],        ← master keyFacts list
  "rescue":    string,          ← rescuePrompt
  "prompts":   Prompt[],        ← full structured prompts (new)
  "scoringGuidance": object,    ← pass/borderline/fail keyed to RCoA 2/1/0 (new)
  "demographics": object | null ← patient demographics (new)
}

Usage:
  python3 scripts/build_scenarios.py
"""

import json
import glob
import os
import sys

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "scenarios")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "webapp", "scenarios.json")


def humanise_topic_id(topic_id: str) -> str:
    """Convert 'iv_anaesthetics' → 'IV Anaesthetics', etc."""
    words = topic_id.replace("_", " ").split()
    # Common all-caps abbreviations
    uppers = {"iv", "lma", "tiva", "mri", "ct", "ecg", "abg", "cns", "cvs"}
    return " ".join(w.upper() if w.lower() in uppers else w.capitalize() for w in words)


def transform_scenario(src: dict) -> dict:
    """Transform a rich schema scenario to the flat webapp shape."""
    # Collect all expectedKeyFacts across prompts → points
    points = []
    probes = []
    for p in src.get("prompts", []):
        probes.append(p["text"])
        points.extend(p.get("expectedKeyFacts", []))

    # Primary topic = first topicTagId, humanised
    topic_ids = src.get("topicTagIds", [])
    topic = humanise_topic_id(topic_ids[0]) if len(topic_ids) > 0 else src.get("domain", "Unknown")

    return {
        "id": src["id"],
        "domain": src.get("domain", ""),
        "topicTagIds": topic_ids,
        "caseId": src.get("caseId"),
        "slotType": src.get("slotType", "any"),
        "caseOrder": src.get("caseOrder", 0),
        "topic": topic,
        "opening": src.get("stem", ""),
        "points": points,
        "probes": probes,
        "facts": src.get("keyFacts", []),
        "rescue": src.get("rescuePrompt", ""),
        # New rich fields — webapp can use these as it matures
        "prompts": src.get("prompts", []),
        "scoringGuidance": src.get("scoringGuidance", {}),
        "demographics": src.get("demographics"),
    }


def main():
    pattern = os.path.join(SCENARIOS_DIR, "*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"ERROR: No scenario files found in {SCENARIOS_DIR}", file=sys.stderr)
        sys.exit(1)

    scenarios = []
    for fpath in files:
        with open(fpath, "r") as f:
            src = json.load(f)
        # Only include active scenarios
        if not src.get("isActive", True):
            print(f"  SKIP (inactive): {os.path.basename(fpath)}")
            continue
        scenarios.append(transform_scenario(src))
        print(f"  ✓ {os.path.basename(fpath)} → {scenarios[-1]['topic']}")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Built {len(scenarios)} scenarios → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

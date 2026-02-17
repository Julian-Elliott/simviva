# FRCA SOE Viva Simulator — ElevenLabs Workflow Architecture

> **Status:** Target architecture. The current PoC uses a single agent with
> one voice — see `agent_config/README.md` for the PoC vs Target comparison.

## Overview

An ElevenLabs **Workflow** (visual graph-based conversation flow)
simulating a Primary FRCA Structured Oral Examination. A single base
agent is extended by **subagent nodes** that override its config
(system prompt, voice, LLM, tools, knowledge base) at each
conversation phase — they are not independent agents.

Two AI examiners conduct a ~14-minute viva across physiology,
pharmacology, physics, clinical measurement, equipment, and applied
anatomy. Scenario data is injected as dynamic variables at session
start — just as real examiners receive their questions beforehand.
Scoring happens post-call via ElevenLabs data collection, and the
candidate receives feedback via the webapp afterwards.

---

## Workflow Diagram

```
┌─────────────────┐
│   EXAMINER 1     │  Subagent node — Voice: George
│  3 question       │  scenario_1_* dynamic vars
│  blocks, ~7 min  │  injected at session start
└──────┬──────────┘
       │ LLM condition: "scenario sufficiently covered"
       ▼
┌─────────────────┐
│   EXAMINER 2     │  Subagent node — Voice: Charlie
│  3 question       │  scenario_2_* dynamic vars
│  blocks, ~7 min  │  injected at session start
└──────┬──────────┘
       │ LLM condition: "scenario completed"
       ▼
┌─────────────────┐
│      END         │  End call node
└─────────────────┘
```

> **Design rationale:** In a real FRCA viva, examiners receive their
> questions before the candidate enters — nothing is selected mid-exam.
> Only the two examiners interact with the candidate. There is no
> coordinator, no in-room debrief. The candidate leaves and receives
> results separately. This workflow mirrors that experience exactly.
> Scenario data is injected at session start via dynamic variables
> (selected by the webapp). Scoring happens post-call via ElevenLabs
> data collection, and the webapp displays results afterwards.

---

## Node Specifications

### 1. EXAMINER 1 (Subagent Node)

**Type:** Subagent node — overrides base agent config.

**Purpose:** Conduct the first short-case scenario (~7 minutes, 3 question blocks).

**Overrides applied:**
- **System prompt:** Append examiner 1 instructions (see `agent_config/nodes/examiner_1/prompt.md` when created)
- **Voice:** `George` (ElevenLabs) — deep, measured, authoritative British male. Stability: 0.7, Similarity: 0.8, Style: 0.3
- **LLM:** May upgrade to a more capable model for complex clinical reasoning
- **Tools:** Include global tools + any examiner-specific tools
- **Knowledge base:** Include global KB; optionally add examiner-specific clinical references

**Dynamic variables available:**
- `candidate_name` (from session start)
- `scenario_1_topic`, `scenario_1_opening`, `scenario_1_points`, etc. (from session start)

**Forward edges (LLM conditions):**

| Label | LLM Condition | Target |
|-------|--------------|--------|
| Scenario complete | `"The examiner has covered three question blocks on the clinical scenario and is ready to hand over."` | → EXAMINER 2 |
| Candidate requests stop | `"The candidate has explicitly requested to stop the examination."` | → END |

---

### 2. EXAMINER 2 (Subagent Node)

**Type:** Subagent node — overrides base agent config.

**Purpose:** Conduct the second short-case scenario (~7 minutes, 3 question blocks).

**Overrides applied:**
- **System prompt:** Append examiner 2 instructions (see `agent_config/nodes/examiner_2/prompt.md` when created)
- **Voice:** `Charlie` (ElevenLabs) — clipped, precise British male. Stability: 0.8, Similarity: 0.75, Style: 0.2
- **LLM:** Same as Examiner 1 (or base)
- **Tools:** Include global tools
- **Knowledge base:** Include global KB

**Dynamic variables available:**
- `candidate_name`
- `scenario_2_topic`, `scenario_2_opening`, `scenario_2_points`, etc.

**Forward edges (LLM conditions):**

| Label | LLM Condition | Target |
|-------|--------------|--------|
| Scenario complete | `"The examiner has covered three question blocks and is closing the scenario."` | → END |
| Candidate requests stop | `"The candidate has explicitly requested to stop."` | → END |

---

### 3. END (End Call Node)

**Type:** End call node — graceful conversation termination.

Terminates the WebRTC/WebSocket connection after Examiner 2 completes.
Mirrors real life — the viva simply ends, and the candidate receives
results separately. The `end_call` system tool can also be triggered
from within any subagent node if needed (e.g. candidate requests to
stop early).

**Post-call scoring:** After the call ends, ElevenLabs' built-in
**data collection** (defined in `agent_config/data_collection.json`)
extracts structured scores and feedback from the conversation
transcript. The webapp fetches these via the results API.

---

## Timing Budget

| Node | Type | Target Duration |
|------|------|----------------|
| Examiner 1 (3 blocks) | Subagent | ~7 min |
| Examiner 2 (3 blocks) | Subagent | ~7 min |
| End | End call | instant |
| **Total** | | **~14 min** |

---

## ElevenLabs Configuration Notes

### Base Agent Settings (inherited by all subagent nodes)
- **Model:** Claude Sonnet 4.5 (current PoC) — can be overridden per subagent node
- **Language:** English (British)
- **Max conversation duration:** 25 minutes (buffer for full workflow)
- **First message:** Handled by the first examiner's subagent node (greeting + scenario stem)

### Realism Settings (configured in `agent_config/`)

| Feature | File | Setting | Effect |
|---------|------|---------|--------|
| **Turn timeout** | `conversation_flow.json` | `turn.turn_timeout: 18` | Candidate has 18 seconds to respond (vs default 7) |
| **Turn eagerness** | `conversation_flow.json` | `turn.turn_eagerness: "patient"` | Agent waits patiently, never cuts off thinking candidates |
| **Soft timeout** | `conversation_flow.json` | `turn.soft_timeout_config.timeout_seconds: -1` | Disabled — no filler prompts during silence |
| **Interruptions** | `conversation_flow.json` | `conversation.client_events: ["audio", "interruption"]` | Candidate can interrupt (rare in vivas, but realistic) |
| **Skip turn** | `tools.json` | System tool `skip_turn` | Agent can stay completely silent while candidate thinks |
| **End call** | `tools.json` | System tool `end_call` | Agent can end the viva gracefully |
| **Multi-voice** | `supported_voices.json` | DrWhitmore + DrHarris voice labels | Two distinct voices for two examiners |
| **Voice speed** | `settings.json` | `voice.speed: 0.95` | Slightly slower for clarity (real examiners speak deliberately) |
| **ASR keywords** | `settings.json` | `asr.keywords: [...]` | 50+ medical terms for accurate speech recognition |
| **Pronunciation** | `pronunciation_dictionary.pls` | PLS alias tags | Correct pronunciation of suxamethonium, rocuronium, etc. |
| **Evaluation** | `evaluation_criteria.json` | 5 success criteria | Post-call automated assessment of examiner performance |

### Edge Configuration
- Use **LLM conditions** (natural language evaluated by the LLM) for
  all transitions — not expressions or keyword matching
- The LLM condition evaluator receives conversation context and decides routing
- Keep condition prompts specific and unambiguous

### Dynamic Variables Pipeline
- All scenario data injected at session start by the webapp: `candidate_name`, `scenario_1_*`, `scenario_2_*`
- System variables auto-populated: `system__conversation_id`, `system__call_duration_secs`, `system__time_utc`
- Dynamic variables persist across all nodes in the workflow
- No mid-conversation tool calls needed — mirrors real life where examiners have questions beforehand

### Knowledge Base Strategy
- **Global KB:** Upload scenario bank as a knowledge base document — available to all nodes
- **Node-specific KB:** Examiner nodes can attach additional clinical reference documents
- Toggle "Include Global Knowledge Base" per subagent node
- For PoC, question data is inlined via dynamic variables in the prompt

### Versioning
- ElevenLabs supports **agent versioning** with branches and traffic deployment
- Each version snapshots: `conversation_config`, `platform_settings`, `workflow`
- Use branches for A/B testing different prompts or workflow structures
- Local config sync (`agent_push.py`/`agent_pull.py`) complements ElevenLabs versioning

### Latency Optimisation
- Set `optimize_streaming_latency` to 1 (balanced)
- Use `eleven_v3_conversational` voice model (lowest latency, expressive mode built-in)
- Keep system prompts under 2000 tokens per subagent node

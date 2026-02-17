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
anatomy, followed by automated scoring and debrief.

---

## Workflow Diagram

```
┌──────────────┐
│   WELCOME     │  Subagent node — Voice: Rachel
│  Greet, get   │  Override: welcome prompt
│  candidate    │
│  name         │
└──────┬───────┘
       │ LLM condition: "candidate confirmed ready"
       ▼
┌─────────────────┐
│ QUESTION SELECT  │  Dispatch tool node
│ select_question  │  success ──► / failure ──► END
│ (webhook)        │
└──────┬──────────┘
       │ success: scenario_1_* dynamic vars set
       ▼
┌─────────────────┐
│   EXAMINER 1     │  Subagent node — Voice: George
│  3 question       │  Override: E1 prompt + voice
│  blocks, ~7 min  │
└──────┬──────────┘
       │ LLM condition: "scenario sufficiently covered"
       ▼
┌─────────────────┐
│ QUESTION SELECT  │  Dispatch tool node (reused)
│ select_question  │  success ──► / failure ──► END
└──────┬──────────┘
       │ success: scenario_2_* dynamic vars set
       ▼
┌─────────────────┐
│   EXAMINER 2     │  Subagent node — Voice: Charlie
│  3 question       │  Override: E2 prompt + voice
│  blocks, ~7 min  │
└──────┬──────────┘
       │ LLM condition: "scenario completed"
       ▼
┌─────────────────┐
│   ASSESSMENT     │  Dispatch tool node
│ assess_performance│  success ──► / failure ──►
└──────┬──────────┘
       │ assessment_* dynamic vars set
       ▼
┌─────────────────┐
│    DEBRIEF       │  Subagent node — Voice: Rachel
│  Scores + feedback│  Override: debrief prompt + voice
└──────┬──────────┘
       │ unconditional
       ▼
┌─────────────────┐
│      END         │  End call node
└─────────────────┘
```

---

## Node Specifications

### 1. WELCOME (Subagent Node)

**Type:** Subagent node — overrides base agent config.

**Purpose:** Greet candidate, obtain surname for formal address, explain format.

**Overrides applied:**
- **System prompt:** Replace with welcome-specific prompt
- **Voice:** `Rachel` (ElevenLabs preset) — warm, professional, British female
- **LLM:** Base model (no override needed)
- **Tools:** Global tools included
- **Knowledge base:** Global KB included

**Prompt summary:**
- Introduce yourself as the exam coordinator
- Ask: "May I have your surname, please?"
- Extract and store `candidate_surname` via dynamic variable assignment
- Brief the candidate: "You will face two examiners, each covering two topics over approximately four minutes each. The examiners will not indicate whether your answers are correct or incorrect — this is normal exam procedure. Shall we begin?"

**Output variables:**
- `candidate_surname` (string) — updated via tool response → dynamic variable assignment

**Forward edge → QUESTION SELECT:**
- Type: LLM condition
- Condition: `"The candidate has provided their name and confirmed they are ready to begin."`

**Timing:** ~60 seconds max.

---

### 2. QUESTION SELECT (Dispatch Tool Node)

**Type:** Dispatch tool node — guarantees tool execution with success/failure routing.

Unlike tools within subagent nodes (which the LLM may or may not call),
a dispatch tool node **always** executes the configured tool. It has
dedicated success and failure edges for deterministic routing.

**Purpose:** Select an unseen question from the question bank for the current examiner.

**Implementation:** Webhook tool that:
1. Receives `examiner_id` (1 or 2), `seen_question_ids` (array)
2. Filters `primary-bank.json` by examiner's category pool
3. Randomly selects an unseen question
4. Returns full question object (stem, expected points, follow-ups, timing)
5. Updates dynamic variables from the tool response (scenario data)

**Tool definition (ElevenLabs format):**
```json
{
  "type": "webhook",
  "name": "select_question",
  "description": "Select the next unseen question for the specified examiner",
  "url": "https://frca.databased.business/api/select-question",
  "method": "POST",
  "parameters": {
    "examiner_id": { "type": "integer", "enum": [1, 2] },
    "seen_ids": { "type": "array", "items": { "type": "string" } }
  }
}
```

**Dynamic variable assignment from response:**
The tool response updates `scenario_N_*` dynamic variables using
dot-notation paths (e.g. `response.topic` → `scenario_1_topic`).

**For the PoC:** Can be simplified — the webapp already picks scenarios
client-side and passes them as dynamic variables at session start.
For the workflow, this dispatch tool replaces that client-side logic.

**Edges:**
- **Success** → EXAMINER 1 or EXAMINER 2 (question payload in dynamic vars)
- **Failure** → END (fallback — no question available)

---

### 3. EXAMINER 1 (Subagent Node)

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
- `scenario_1_topic`, `scenario_1_opening`, `scenario_1_points`, etc. (from dispatch tool or session start)

**Forward edges (LLM conditions):**

| Label | LLM Condition | Target |
|-------|--------------|--------|
| Scenario complete | `"The examiner has covered three question blocks on the clinical scenario and is ready to hand over."` | → QUESTION SELECT (for Examiner 2) |
| Candidate requests stop | `"The candidate has explicitly requested to stop the examination."` | → ASSESSMENT |

---

### 4. EXAMINER 2 (Subagent Node)

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
| Scenario complete | `"The examiner has covered three question blocks and is closing the scenario."` | → ASSESSMENT |
| Candidate requests stop | `"The candidate has explicitly requested to stop."` | → ASSESSMENT |

---

### 5. ASSESSMENT (Dispatch Tool Node)

**Type:** Dispatch tool node — guaranteed execution with success/failure routing.

**Purpose:** Analyse the full transcript and score against model answers.

**Implementation:** Webhook tool that:
1. Receives the conversation transcript (via `system__conversation_id`)
2. Compares candidate responses against `expectedPoints` for each scenario
3. Assigns each question a per-question mark on the RCoA 0/1/2 scale
4. Returns structured feedback payload
5. Updates dynamic variables with scores for the debrief node

**Tool definition:**
```json
{
  "type": "webhook",
  "name": "assess_performance",
  "description": "Score the candidate's viva performance against model answers",
  "url": "https://frca.databased.business/api/assess",
  "method": "POST",
  "parameters": {
    "conversation_id": { "type": "string" }
  }
}
```

**Dynamic variable assignment from response:**
- `assessment_q1_mark` ← `response.question_1_mark`
- `assessment_q2_mark` ← `response.question_2_mark`
- `assessment_feedback` ← `response.feedback_summary`

**For the PoC:** This is handled by ElevenLabs' built-in data collection
(post-call extraction) defined in `agent_config/data_collection.json`.
For the workflow, a dedicated dispatch tool replaces post-call extraction
with in-call scoring so the debrief node can reference results.

**Edges:**
- **Success** → DEBRIEF (scores in dynamic variables)
- **Failure** → DEBRIEF (deliver generic feedback without specific scores)

---

### 6. DEBRIEF (Subagent Node)

**Type:** Subagent node — overrides base agent config.

**Purpose:** Deliver warm, constructive feedback with specific scores and recommendations.

**Overrides applied:**
- **System prompt:** Replace with debrief-specific prompt (see `agent_config/nodes/debrief/prompt.md` when created)
- **Voice:** `Rachel` (same as Welcome) — continuity, warm closure
- **LLM:** Base model
- **Tools:** End call tool included
- **Knowledge base:** Global KB (for reference if candidate asks follow-up questions)

**Dynamic variables available:**
- `candidate_name`
- `assessment_q1_mark`, `assessment_q2_mark`, `assessment_feedback` (from dispatch tool)

**Forward edge → END:**
- Type: Unconditional (automatic progression after debrief completes)

---

### 7. END (End Call Node)

**Type:** End call node — graceful conversation termination.

Terminates the WebRTC/WebSocket connection after the debrief node
completes. The `end_call` system tool can also be triggered from within
any subagent node if needed (e.g. candidate requests to stop early).

---

## Timing Budget

| Node | Type | Target Duration |
|------|------|----------------|
| Welcome | Subagent | ~1 min |
| Question Select 1 | Dispatch tool | <1 sec |
| Examiner 1 (3 blocks) | Subagent | ~7 min |
| Question Select 2 | Dispatch tool | <1 sec |
| Examiner 2 (3 blocks) | Subagent | ~7 min |
| Assessment | Dispatch tool | 2-3 sec |
| Debrief | Subagent | 3-4 min |
| End | End call | instant |
| **Total** | | **~18-20 min** |

---

## ElevenLabs Configuration Notes

### Base Agent Settings (inherited by all subagent nodes)
- **Model:** Claude Sonnet 4.5 (current PoC) — can be overridden per subagent node
- **Language:** English (British)
- **Max conversation duration:** 30 minutes (buffer for full workflow)
- **First message:** Handled by Welcome subagent node
- **Turn eagerness:** Patient (gives candidates time to formulate answers)

### Edge Configuration
- Use **LLM conditions** (natural language evaluated by the LLM) for
  all transitions — not expressions or keyword matching
- The LLM condition evaluator receives conversation context and decides routing
- Keep condition prompts specific and unambiguous
- Dispatch tool nodes use **success/failure edges** (deterministic, not LLM-evaluated)

### Dynamic Variables Pipeline
- Variables injected at session start: `candidate_name`, all `scenario_*` vars
- Variables updated by dispatch tools: `assessment_*` scores and feedback
- System variables auto-populated: `system__conversation_id`, `system__call_duration_secs`, `system__time_utc`
- Dynamic variables persist across all nodes in the workflow

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
- Use `eleven_v3_conversational` voice model for lowest latency
- Consider using a faster LLM for simple nodes (Welcome, Debrief)
- Keep system prompts under 2000 tokens per subagent node

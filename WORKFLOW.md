# FRCA SOE Viva Simulator — ElevenLabs Workflow Architecture

## Overview

A multi-node ElevenLabs Conversational AI workflow simulating a Primary FRCA Structured Oral Examination. Two AI examiners conduct a 20-minute viva across physiology, pharmacology, physics, clinical measurement, equipment, and applied anatomy, followed by automated scoring and debrief.

---

## Workflow Diagram

```
┌─────────────┐
│   WELCOME    │  (Subagent node)
│  Get name,   │
│  set context │
└──────┬───────┘
       │ candidate_name extracted
       ▼
┌─────────────────┐
│ QUESTION SELECT  │  (Dispatch tool)
│ Pick topic +     │
│ question for E1  │
└──────┬──────────┘
       │ question payload
       ▼
┌─────────────────┐
│   EXAMINER 1     │  (Subagent node — Voice A)
│ Physiology /     │
│ Pharmacology     │
│ 2 × 4-min topics│
└──────┬──────────┘
       │ LLM condition: "8 minutes elapsed OR 2 topics completed"
       ▼
┌─────────────────┐
│ QUESTION SELECT  │  (Dispatch tool — reused)
│ Pick topic +     │
│ question for E2  │
└──────┬──────────┘
       │ question payload
       ▼
┌─────────────────┐
│   EXAMINER 2     │  (Subagent node — Voice B)
│ Physics / Equip /│
│ Applied Anatomy  │
│ 2 × 4-min topics│
└──────┬──────────┘
       │ LLM condition: "8 minutes elapsed OR 2 topics completed"
       ▼
┌─────────────────┐
│   ASSESSMENT     │  (Dispatch tool)
│ Score transcript │
│ vs model answers │
└──────┬──────────┘
       │ scores + feedback payload
       ▼
┌─────────────────┐
│    DEBRIEF       │  (Subagent node — Voice C)
│ Deliver feedback │
│ RCoA 4-point     │
│ scale scores     │
└─────────────────┘
```

---

## Node Specifications

### 1. WELCOME (Subagent Node)

**Purpose:** Greet candidate, obtain surname for formal address, explain format.

**Voice:** `Rachel` (ElevenLabs preset) — warm, professional, British female.

**System prompt summary:**
- Introduce yourself as the exam coordinator
- Ask: "May I have your surname, please?"
- Extract and store `candidate_surname` in session state
- Brief the candidate: "You will face two examiners, each covering two topics over approximately four minutes each. The examiners will not indicate whether your answers are correct or incorrect — this is normal exam procedure. Shall we begin?"

**Output variables:**
- `candidate_surname` (string)

**Edge → QUESTION SELECT:**
- Condition: `candidate_surname` is non-empty AND candidate confirms ready

**Timing:** ~60 seconds max.

---

### 2. QUESTION SELECT (Dispatch Tool / Custom Function)

**Purpose:** Select an unseen question from the question bank for the current examiner.

**Implementation:** Custom tool (server-sent or webhook) that:
1. Receives `examiner_id` (1 or 2), `seen_question_ids` (array)
2. Filters `primary-bank.json` by examiner's category pool
3. Randomly selects an unseen question
4. Returns full question object (stem, expected points, follow-ups, timing)

**Tool definition (ElevenLabs format):**
```json
{
  "name": "select_question",
  "description": "Select the next unseen question for the specified examiner",
  "parameters": {
    "examiner_id": { "type": "integer", "enum": [1, 2] },
    "seen_ids": { "type": "array", "items": { "type": "string" } }
  }
}
```

**For the PoC:** Can be simplified — embed the question bank as knowledge base text and let the LLM pick. For production, use a proper tool endpoint.

**Edge → EXAMINER 1 or EXAMINER 2:**
- Direct pass-through with question payload injected into examiner's context

---

### 3. EXAMINER 1 (Subagent Node)

**Purpose:** Conduct physiology and pharmacology viva.

**Voice:** `George` (ElevenLabs) — deep, measured, authoritative British male. Stability: 0.7, Similarity: 0.8, Style: 0.3.

**System prompt:** See `prompts/examiner-1.md`

**Input variables:**
- `candidate_surname`
- `current_question` (from dispatch)
- `topic_number` (1 or 2)

**Internal state tracking:**
- Topics covered count
- Time elapsed (use ElevenLabs conversation duration or token count as proxy)
- Follow-up triggers matched

**Edge conditions (LLM-evaluated):**
| Condition | Target |
|-----------|--------|
| First topic complete (~5 min), second topic not started | → QUESTION SELECT (for topic 2) |
| Both topics complete OR ~8 min elapsed | → QUESTION SELECT (for Examiner 2) |
| Candidate requests to stop | → ASSESSMENT |

**LLM condition prompt for topic transition:**
```
Has the examiner covered the current topic sufficiently (at least 3-4 exchanges) 
AND has approximately 5 minutes of conversation occurred on this topic? 
If yes, transition. If the candidate is completely stuck after a rescue question, 
also transition.
```

---

### 4. EXAMINER 2 (Subagent Node)

**Purpose:** Conduct physics, equipment, clinical measurement, and applied anatomy viva.

**Voice:** `Charlie` (ElevenLabs) — clipped, precise British male. Stability: 0.8, Similarity: 0.75, Style: 0.2.

**System prompt:** See `prompts/examiner-2.md`

**Same structure as Examiner 1** but with different topic categories and voice.

**Edge conditions:** Same pattern — two topics, then → ASSESSMENT.

---

### 5. ASSESSMENT (Dispatch Tool)

**Purpose:** Analyse the full transcript and score against model answers.

**Implementation:** Custom tool or LLM-as-judge prompt that:
1. Receives full conversation transcript
2. Compares candidate responses against `expectedPoints` for each question
3. Scores each topic on RCoA 4-point scale
4. Generates structured feedback

**Tool definition:**
```json
{
  "name": "assess_performance",
  "description": "Score the candidate's viva performance against model answers",
  "parameters": {
    "transcript": { "type": "string" },
    "questions_asked": { "type": "array", "items": { "type": "object" } }
  }
}
```

**Output payload:**
```json
{
  "overall_score": 3,
  "topic_scores": [
    { "topic": "Cardiovascular Physiology", "score": 3, "key_gaps": [...], "strengths": [...] }
  ],
  "notable_moments": [...],
  "recommendations": [...]
}
```

**For the PoC:** Use a subagent with a scoring system prompt instead of a real tool. The subagent silently processes and passes structured JSON to the Debrief node.

**Edge → DEBRIEF:** Direct pass-through with scores payload.

---

### 6. DEBRIEF (Subagent Node)

**Purpose:** Deliver warm, constructive feedback with specific scores and recommendations.

**Voice:** `Rachel` (same as Welcome) — continuity, warm closure.

**System prompt:** See `prompts/debrief.md`

**Input variables:**
- `candidate_surname`
- `assessment_payload` (scores, gaps, strengths, notable moments)

**No outgoing edge** — conversation ends here.

---

## Timing Budget

| Node | Target Duration |
|------|----------------|
| Welcome | 1 min |
| Question Select 1 | <1 sec (tool call) |
| Examiner 1, Topic 1 | 5 min |
| Question Select 2 | <1 sec |
| Examiner 1, Topic 2 | 5 min |
| Question Select 3 | <1 sec |
| Examiner 2, Topic 1 | 5 min |
| Question Select 4 | <1 sec |
| Examiner 2, Topic 2 | 5 min |
| Assessment | 2-3 sec (processing) |
| Debrief | 3-4 min |
| **Total** | **~24-26 min** |

---

## ElevenLabs Dashboard Configuration Notes

### Global Agent Settings
- **Model:** GPT-4o or Claude Sonnet (whichever ElevenLabs supports for your tier)
- **Language:** English (British)
- **Max conversation duration:** 25 minutes (buffer)
- **First message:** Handled by Welcome node

### Edge Configuration
- Use **LLM conditions** (not keyword matching) for all transitions
- The LLM condition evaluator receives the last N messages and decides routing
- Keep condition prompts specific and unambiguous

### State/Variables
- Use ElevenLabs' `dynamic_variables` or `custom_llm_extra_body` to pass:
  - `candidate_surname`
  - `current_question_id`
  - `seen_question_ids`
  - `topic_count`

### Knowledge Base
- Upload `primary-bank.json` as a knowledge base document
- Reference it in examiner system prompts
- For PoC, can inline key questions directly in prompts

### Latency Optimisation
- Set `optimize_streaming_latency` to 3 (aggressive)
- Use Turbo v2.5 voice models for lowest latency
- Keep system prompts under 2000 tokens each

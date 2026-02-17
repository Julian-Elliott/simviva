# FRCA SOE Viva Simulator — ElevenLabs Setup Guide

Step-by-step guide to building the workflow in ElevenLabs.

---

## Prerequisites

- ElevenLabs account (Creator tier or above for Conversational AI)
- Access to Conversational AI → Agents (elevenlabs.io/app/conversational-ai)
- The files from this repo: prompts, question bank

---

## Step 1: Create the Agent

1. Go to **Conversational AI** → **Create Agent**
2. Choose **Blank template**
3. Name: `FRCA SOE Viva Simulator`
4. Language: **English**
5. LLM: Claude 4.6
6. Set max conversation duration: **25 minutes**

---

## Step 2: Create the Workflow

In the agent editor, switch to **Workflow** mode (not single-prompt mode).

> **Design principle:** In a real FRCA viva, only the two examiners
> interact with the candidate. Examiners receive their questions
> beforehand — nothing is selected mid-exam. This workflow mirrors
> that experience. Scenario data is injected at session start via
> dynamic variables.

### Node 1: Examiner 1

- **Type:** Subagent
- **Name:** `examiner_1`
- **Voice:** `George` (British male, deep, measured)
  - If George unavailable, use `Daniel` or `James`
  - Stability: 0.70
  - Clarity + Similarity: 0.80
  - Style: 0.30 (low expressiveness = poker face)
  - Speaker Boost: ON
- **System prompt:** Paste contents of `prompts/examiner-1.md`
- **Dynamic variables:**
  - `{{candidate_name}}` — from session start (webapp)
  - `{{scenario_1_topic}}`, `{{scenario_1_opening}}`, etc. — from session start (webapp)
- **First message:** Leave blank (the system prompt instructs the examiner to open with the stem question)

### Node 2: Examiner 2

- **Type:** Subagent
- **Name:** `examiner_2`
- **Voice:** `Charlie` (British male, clipped, precise)
  - If Charlie unavailable, use `Liam` or `Patrick`
  - Stability: 0.80
  - Clarity + Similarity: 0.75
  - Style: 0.20 (minimal expressiveness)
  - Speaker Boost: ON
- **System prompt:** Paste contents of `prompts/examiner-2.md`
- **Dynamic variables:**
  - `{{candidate_name}}` — from session start (webapp)
  - `{{scenario_2_topic}}`, `{{scenario_2_opening}}`, etc. — from session start (webapp)

### Node 3: END

- **Type:** End call
- **Name:** `end`
- No voice, prompt, or LLM configuration needed — this node simply
  terminates the WebRTC/WebSocket connection when reached.
- Mirrors real life: the viva ends and the candidate leaves the room.
  Post-call data collection runs automatically after the call closes.

---

## Step 3: Configure Edges

In the workflow canvas, draw edges between nodes:

| From | To | Condition |
|------|----|-----------|
| examiner_1 | examiner_2 | LLM: "Examiner has covered the clinical scenario sufficiently and is ready to hand over" |
| examiner_2 | END | LLM: "Examiner has completed the scenario and is closing" |

### LLM Condition Tips
- Keep conditions short and specific
- Test edge cases: what if the candidate stops talking? What if they ask to skip?
- Add a fallback timeout edge (if available in your ElevenLabs tier)

---

## Step 4: Add Knowledge Base (Question Bank)

1. Go to **Knowledge Base** in your agent settings
2. Upload `questions/primary-bank.json` as a document
3. In examiner system prompts, add: "Reference the question bank knowledge base for expected answers and follow-up triggers"

**PoC alternative:** Paste 2–3 questions directly into each examiner's system prompt rather than using the knowledge base.

---

## Step 5: PoC Simplification (Recommended for Monday Demo)

For the Monday demo, the target workflow **is** the simplified version —
just two examiner nodes with an LLM condition edge between them:

```
EXAMINER 1 → EXAMINER 2 → END
```

- **Scenario data** is injected at session start via dynamic variables (selected by the webapp)
- **Scoring** uses post-call data collection (already configured in `data_collection.json`)
- **No webhooks or external servers needed**

---

## Step 6: Realism Configuration

The following config files are synced to ElevenLabs via `agent_push.py`:

### Turn & Conversation Flow (`agent_config/conversation_flow.json`)
- **Turn timeout:** 18 seconds (candidates need time to think — far more than the default 7s)
- **Turn eagerness:** `"patient"` — never cuts off a thinking candidate
- **Soft timeout:** Disabled (`-1`) — no automatic filler prompts during silence
- **Client events:** Includes `"interruption"` — candidate can interrupt if needed
- **Max duration:** 25 minutes total

### System Tools (`agent_config/tools.json`)
- **`skip_turn`** — allows the examiner to stay completely silent while the candidate thinks (critical for realism — real examiners don't fill silence)
- **`end_call`** — graceful conversation termination

### Multi-Voice (`agent_config/supported_voices.json`)
- **DrWhitmore** (George voice) — for Examiner 1
- **DrHarris** (Charlie voice) — for Examiner 2
- The system prompt uses `<DrWhitmore>...</DrWhitmore>` and `<DrHarris>...</DrHarris>` voice tags

### ASR Keywords (`agent_config/settings.json → asr.keywords`)
- 50+ anaesthetic terms (suxamethonium, rocuronium, cricothyroidotomy, etc.)
- Helps ElevenLabs' speech recognition accurately transcribe medical terminology

### Pronunciation Dictionary (`agent_config/pronunciation_dictionary.pls`)
Upload the PLS file to ElevenLabs:
1. Go to **Speech** → **Pronunciation Dictionaries** (or agent Voice tab → Pronunciation)
2. Upload `pronunciation_dictionary.pls`
3. Copy the dictionary ID and version ID
4. Paste into `agent_config/pronunciation_locator.json`
5. Run `agent_push.py` to attach the dictionary to the agent

> **Note:** Uses alias tags (not phoneme tags) for compatibility with
> `eleven_v3_conversational`. Phoneme tags only work with Flash/Turbo models.

### Evaluation Criteria (`agent_config/evaluation_criteria.json`)
5 criteria for automated post-call evaluation:
- Examiner character maintained
- Three question blocks per examiner
- Correct SOE stem delivery
- Appropriate timing
- Clean examiner handover

---

## Step 7: Voice Testing

Before the demo, test each voice:

1. Go to **Voice Lab** → test `George` / `Charlie` with sample examiner lines:
   - "I see. Can you tell me about the factors affecting cardiac output?"
   - "Are you sure about that?"
   - "Mm-hmm. What else?"
   - "Let's move on."
2. Adjust stability/similarity if they sound too expressive or too robotic
3. Lower **Style** for examiners (poker face)

### Voice Alternatives (if defaults don't sound right)

| Role | Primary | Backup 1 | Backup 2 |
|------|---------|----------|----------|
| Examiner 1 | George | Daniel | Adam |
| Examiner 2 | Charlie | Liam | Callum |

---

## Step 8: Test the Full Flow

1. **Test each node in isolation** first — use the "Test" button on each subagent
2. Test that voice switching works between nodes
3. Run a full end-to-end session yourself, playing the candidate
4. Time each section — aim for 5 min per topic
5. Check edge transitions fire correctly
6. Verify post-call results appear correctly in the webapp

### Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Examiner sounds too friendly | Lower Style to 0.1–0.2, add "Never express warmth" to prompt |
| Transitions don't fire | Simplify LLM condition text, add explicit trigger phrases to examiner prompts |
| Variables don't pass between nodes | Check dynamic_variables are correctly named and mapped |
| Post-call results missing | Check data_collection.json fields match the analysis API response |
| Voice latency too high | Use Turbo v2.5 voice model, set `optimize_streaming_latency` to 3 |

--
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

### Node 1: Welcome

- **Type:** Subagent
- **Name:** `welcome`
- **Voice:** `Rachel` (British, warm, professional)
  - Stability: 0.75
  - Clarity + Similarity: 0.80
  - Style: 0.4
- **System prompt:**
  ```
  You are the examination coordinator for a Primary FRCA practice viva.
  
  1. Greet the candidate warmly but professionally
  2. Ask: "May I have your surname, please?"
  3. Store their surname
  4. Explain the format: "You'll face two examiners, each covering two topics 
     for about four minutes each. The examiners won't indicate whether your 
     answers are correct — this is normal exam procedure."
  5. Ask: "Are you ready to begin?"
  ```
- **Output variables:** Add `candidate_surname` (string)
- **First message:** "Good afternoon. Welcome to your Primary FRCA practice viva. Before we begin, may I have your surname, please?"

### Node 2: Question Select (Examiner 1, Topic 1)

- **Type:** Dispatch (Tool call)
- **Name:** `select_q_e1t1`

**For the PoC (no external server):** Use a Subagent node instead:
- System prompt: Include the full question bank JSON. Instruct it to select one PHYSIOLOGY or PHARMACOLOGY question at random and output the stem question and follow-ups as structured data.
- This node should speak nothing — set its first message to trigger an immediate edge transition.

**For production:** Create a custom tool:
1. Go to **Tools** → **Create Tool**
2. Name: `select_question`
3. Method: POST
4. URL: Your webhook endpoint
5. Body schema:
   ```json
   {
     "examiner_id": 1,
     "seen_ids": [],
     "categories": ["PHYSIOLOGY", "PHARMACOLOGY"]
   }
   ```

### Node 3: Examiner 1

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
  - `{{candidate_surname}}` — from welcome node
  - `{{current_question}}` — from question select
- **First message:** Leave blank (the system prompt instructs the examiner to open with the stem question)

### Node 4: Question Select (Examiner 1, Topic 2)

- Same as Node 2 but pass `seen_ids` containing the first question's ID
- Select from remaining PHYSIOLOGY/PHARMACOLOGY questions

### Node 5: Examiner 1 (Topic 2)

- Same subagent as Node 3, new question context
- **Alternative PoC simplification:** Keep Examiner 1 as a single node and include 2 questions in the system prompt, instructing them to cover both sequentially

### Node 6: Question Select (Examiner 2)

- Same tool, but `examiner_id: 2`, categories: `["PHYSICS", "EQUIPMENT", "ANATOMY"]`

### Node 7: Examiner 2

- **Type:** Subagent
- **Name:** `examiner_2`
- **Voice:** `Charlie` (British male, clipped, precise)
  - If Charlie unavailable, use `Liam` or `Patrick`
  - Stability: 0.80
  - Clarity + Similarity: 0.75
  - Style: 0.20 (minimal expressiveness)
  - Speaker Boost: ON
- **System prompt:** Paste contents of `prompts/examiner-2.md`

### Node 8: Assessment

- **Type:** Subagent (silent processing)
- **Name:** `assessment`
- **Voice:** None (this node doesn't speak — it processes and passes data)
- **System prompt:**
  ```
  You are an assessment engine. You have received the full conversation 
  transcript of a Primary FRCA viva. Score each topic on the RCoA 4-point 
  scale (4=Pass+, 3=Pass, 2=Borderline, 1=Fail). 
  
  Output a JSON object with: overall_score, topic_scores (with gaps and 
  strengths for each), notable_moments (2-3 specific exchanges), and 
  recommendations. Reference the expected points from the question bank.
  
  Do not speak to the candidate. Output structured data only.
  ```
- **Transition:** Immediate edge to Debrief with assessment payload

### Node 9: Debrief

- **Type:** Subagent
- **Name:** `debrief`
- **Voice:** `Rachel` (same as Welcome — warm continuity)
  - Stability: 0.65
  - Clarity + Similarity: 0.85
  - Style: 0.50 (warmer, more expressive for feedback)
- **System prompt:** Paste contents of `prompts/debrief.md`

---

## Step 3: Configure Edges

In the workflow canvas, draw edges between nodes:

| From | To | Condition |
|------|----|-----------|
| welcome | select_q_e1t1 | LLM: "Candidate has provided surname and confirmed ready" |
| select_q_e1t1 | examiner_1 | Auto (tool completes) |
| examiner_1 | select_q_e1t2 | LLM: "Examiner has said 'let's move on' after covering first topic adequately (~4 min)" |
| select_q_e1t2 | examiner_1_t2 | Auto |
| examiner_1_t2 | select_q_e2t1 | LLM: "Examiner has concluded with 'my colleague will continue' or similar handover" |
| select_q_e2t1 | examiner_2 | Auto |
| examiner_2 | select_q_e2t2 | LLM: "Examiner has moved on from first topic after ~4 minutes" |
| select_q_e2t2 | examiner_2_t2 | Auto |
| examiner_2_t2 | assessment | LLM: "Examiner has said 'that's my section complete'" |
| assessment | debrief | Auto (assessment processing complete) |

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

For the Monday demo, simplify to reduce failure points:

### Simplified 4-Node Workflow
```
WELCOME → EXAMINER 1 → EXAMINER 2 → DEBRIEF
```

- **Embed questions directly** in each examiner's system prompt (pick 2 questions each)
- **Skip the question select tool** — hardcode the questions
- **Skip the assessment tool** — have the debrief node assess the transcript itself
- **Use LLM conditions** for transitions between examiners

### Minimal System Prompt Template for PoC Examiners
Include at the bottom of each examiner prompt:
```
## Questions for This Session

### Topic 1: [Topic Name]
Stem: "[stem question]"
Key points to listen for: [list]
Follow-ups: [list]

### Topic 2: [Topic Name]
Stem: "[stem question]"  
Key points to listen for: [list]
Follow-ups: [list]

Start with Topic 1. After approximately 4 minutes, transition to Topic 2.
```

---

## Step 6: Voice Testing

Before the demo, test each voice:

1. Go to **Voice Lab** → test `George` / `Charlie` / `Rachel` with sample examiner lines:
   - "I see. Can you tell me about the factors affecting cardiac output?"
   - "Are you sure about that?"
   - "Mm-hmm. What else?"
   - "Let's move on."
2. Adjust stability/similarity if they sound too expressive or too robotic
3. Lower **Style** for examiners (poker face), higher for debrief (warm)

### Voice Alternatives (if defaults don't sound right)

| Role | Primary | Backup 1 | Backup 2 |
|------|---------|----------|----------|
| Examiner 1 | George | Daniel | Adam |
| Examiner 2 | Charlie | Liam | Callum |
| Welcome/Debrief | Rachel | Charlotte | Lily |

---

## Step 7: Test the Full Flow

1. **Test each node in isolation** first — use the "Test" button on each subagent
2. Test that voice switching works between nodes
3. Run a full end-to-end session yourself, playing the candidate
4. Time each section — aim for 4 min per topic
5. Check edge transitions fire correctly
6. Verify the debrief references specific things you said

### Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Examiner sounds too friendly | Lower Style to 0.1–0.2, add "Never express warmth" to prompt |
| Transitions don't fire | Simplify LLM condition text, add explicit trigger phrases to examiner prompts |
| Variables don't pass between nodes | Check dynamic_variables are correctly named and mapped |
| Debrief is generic | Ensure transcript context passes through; for PoC, the LLM should have conversation history |
| Voice latency too high | Use Turbo v2.5 voice model, set `optimize_streaming_latency` to 3 |

--
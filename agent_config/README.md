# Agent Configuration — Single Source of Truth

This directory holds the canonical configuration for the ElevenLabs
Conversational AI agent. Every setting that matters lives here in
plain, diffable files.

## Agent Goal

Simulate a **Primary FRCA Structured Oral Examination** (SOE) viva.
Two AI examiners each present a clinical scenario (short cases), probe
the candidate's anaesthetic knowledge for ~7 minutes each, then the
system scores performance on the RCoA 0/1/2 per-question scale.
Feedback is delivered asynchronously via the webapp — mirroring real
life where candidates leave and receive results separately.

---

## Architecture: PoC vs Target

### Current PoC — Single Agent, Single Voice

One ElevenLabs agent (`agent_7401kgyecx7mewbv2c8gs5f0ff39`) handles
the entire conversation. Dr Whitmore and Dr Harris are role-played via
the system prompt, but use the same voice. Scoring happens
via ElevenLabs' built-in **data collection** (post-call extraction).

```
 Candidate                  ElevenLabs Agent
 ────────                   ─────────────────
     │  WebRTC audio + dynamic vars  │
     │ ──────────────────────────► │
     │                               │  Single system prompt handles:
     │                               │   • Examiner 1 (Dr Whitmore)
     │                               │   • Examiner 2 (Dr Harris)
     │                               │   • Post-call data collection
     │  ◄──────────────────────── │
     │   TTS audio (one voice)       │
     │                               │
     ▼                               ▼
 webapp/index.html          results-proxy → /api/results/:id
  fetches scores              fetches conversation analysis
```

### Target — ElevenLabs Workflow (Multi-Node, Multi-Voice)

An ElevenLabs **Workflow** composed of subagent nodes and edges with
LLM conditions. Each node can override the base agent's configuration
(system prompt, voice, LLM, tools, knowledge base) without creating
separate agents. Scenario data is injected at session start via dynamic
variables — just as real examiners receive their questions beforehand.

```
┌─────────────────┐
│   EXAMINER 1     │  Subagent node — Voice: George
│  Override: E1     │  Override prompt (append), LLM, voice
│  prompt + voice   │  Tools: global tools included
└──────┬──────────┘
       │ LLM condition: "examiner has covered scenario sufficiently"
       ▼
┌─────────────────┐
│   EXAMINER 2     │  Subagent node — Voice: Charlie
│  Override: E2     │  Override prompt (append), LLM, voice
│  prompt + voice   │
└──────┬──────────┘
       │ LLM condition: "examiner has completed scenario"
       ▼
┌─────────────────┐
│      END         │  End call node
└─────────────────┘
```

### ElevenLabs Workflow Primitives Used

| Primitive | SimViva Usage | Docs Reference |
|-----------|--------------|----------------|
| **Subagent node** | Override base agent config at each conversation phase (prompt, voice, LLM, tools, KB) | [Workflows → Subagent nodes](https://elevenlabs.io/docs/agents-platform/customization/agent-workflows) |
| **End call node** | Graceful conversation termination after Examiner 2 completes | [System tools → End call](https://elevenlabs.io/docs/agents-platform/customization/tools/system-tools/end-call) |
| **Forward edge (LLM condition)** | Natural language conditions evaluated by LLM to determine transitions (e.g. "has the examiner completed the scenario?") | [Workflows → Edges](https://elevenlabs.io/docs/agents-platform/customization/agent-workflows) |
| **Dynamic variables** | Per-conversation personalisation — candidate name, scenario data injected at session start | [Personalisation → Dynamic variables](https://elevenlabs.io/docs/agents-platform/customization/personalization/dynamic-variables) |
| **Data collection** | Post-call structured extraction — scores, summaries, feedback | [Conversation analysis](https://elevenlabs.io/docs/agents-platform/customization/agent-analysis) |

### Key Difference: Subagent Nodes ≠ Separate Agents

In an ElevenLabs Workflow, subagent nodes **override the base agent's
config** — they are not independent agents. Each node can:

- **Append or replace** the system prompt
- Switch to a **different voice** (e.g. George → Charlie)
- Use a **different LLM** (e.g. faster model for simple nodes)
- Add/remove **tools** (include or exclude global tools)
- Attach **node-specific knowledge base** documents

The base agent config (this directory) provides the defaults that all
nodes inherit unless explicitly overridden.

---

## Files

| File | What it controls | API path |
|------|-----------------|----------|
| `system_prompt.md` | Full system prompt sent to the LLM | `conversation_config.agent.prompt.prompt` |
| `data_collection.json` | Post-conversation data extraction fields (7 fields) | `platform_settings.data_collection` |
| `settings.json` | Voice, LLM, first message, agent name, language, dynamic variables, ASR keywords | `conversation_config.agent.*`, `conversation_config.tts.*`, `conversation_config.asr` |
| `conversation_flow.json` | Turn timeout (18s), turn eagerness (patient), soft timeout (disabled), interruptions | `conversation_config.turn`, `conversation_config.conversation` |
| `tools.json` | System tools — `skip_turn` (examiner silence), `end_call` | `conversation_config.agent.prompt.tools` |
| `supported_voices.json` | Multi-voice — Dr Whitmore (George) + Dr Harris (Charlie) | `conversation_config.tts.supported_voices` |
| `evaluation_criteria.json` | Post-call success evaluation criteria (5 criteria) | `platform_settings.evaluation.criteria` |
| `pronunciation_dictionary.pls` | PLS lexicon for medical term pronunciation (alias tags) | Uploaded separately, referenced via locator |
| `pronunciation_locator.json` | Pronunciation dictionary ID reference (after manual upload) | `conversation_config.tts.pronunciation_dictionary_locators` |

---

## End-to-End Data Flow

### 1. Webapp loads scenarios

`webapp/index.html` fetches `scenarios.json` (compiled by
`scripts/build_scenarios.py` from `data/scenarios/*.json`), picks two
random scenarios via `pickTwo()`, and builds a `dynamicVars` object.

### 2. Session starts with dynamic variables

```js
Conversation.startSession({
  agentId: "<agent-id>",
  dynamicVariables: {
    candidate_name: "Smith",
    scenario_1_topic: "Malignant Hyperthermia",
    scenario_1_opening: "A 25-year-old ...",
    // ... all 15 variables
  }
})
```

### 3. Agent conducts the viva

The system prompt uses `{{variable}}` placeholders that ElevenLabs
resolves at runtime. The agent role-plays both examiners (PoC) or
subagent nodes handle each examiner (target workflow).

### 4. Post-call data collection

After the call ends, ElevenLabs extracts structured data defined in
`data_collection.json`:

| Field | Purpose |
|-------|---------|
| `question_1_mark` | RCoA 0/1/2 mark + justification for Dr Whitmore's scenario |
| `question_2_mark` | RCoA 0/1/2 mark + justification for Dr Harris's scenario |
| `topic_1_summary` | Performance summary for scenario 1 |
| `topic_2_summary` | Performance summary for scenario 2 |
| `key_facts_covered` | Semicolon-separated list of correctly stated facts |
| `key_facts_missed` | Semicolon-separated list of missed/incorrect facts |
| `areas_for_improvement` | 2-3 specific revision topics with reasons |

### 5. Webapp fetches results

`webapp/index.html` polls `/api/results/{conversationId}` (proxied by
`results-proxy.py` on port 3001) which calls the ElevenLabs
conversation analysis API and returns the extracted data.

---

## Dynamic Variables

| Variable | Example Value | Used In |
|----------|--------------|---------|
| `candidate_name` | `"Smith"` | First message, prompt |
| `scenario_1_topic` | `"Malignant Hyperthermia"` | Examiner 1 section |
| `scenario_1_opening` | `"A 25-year-old..."` | Examiner 1 stem |
| `scenario_1_points` | `"Dantrolene dose..."` | Examiner 1 expected answers |
| `scenario_1_probes` | `"What triggers..."` | Examiner 1 follow-ups |
| `scenario_1_facts` | `"Calcium release..."` | Examiner 1 key facts |
| `scenario_1_rescue` | `"What is the mechanism..."` | Examiner 1 rescue question |
| `scenario_1_scoring` | `"2 = structured answer..."` | Examiner 1 marking rubric |
| `scenario_2_*` | *(same pattern as above)* | Examiner 2 section |

System dynamic variables (auto-populated by ElevenLabs):
`system__agent_id`, `system__conversation_id`, `system__time_utc`,
`system__call_duration_secs`, etc.

---

## Config Sync Workflow

```
 ┌──────────────┐      agent_push.py      ┌──────────────────┐
 │ agent_config/ │  ──────────────────►   │  ElevenLabs API  │
 │  (local git)  │  ◄──────────────────   │  (live agent)    │
 └──────────────┘      agent_pull.py      └──────────────────┘
```

### Push local → ElevenLabs

Edit the files here, then push them to the live agent:

```bash
source .env && python3 scripts/agent_push.py        # live push
source .env && python3 scripts/agent_push.py --dry-run  # preview only
```

### Pull ElevenLabs → local

Fetch the live agent's current config and overwrite these files:

```bash
source .env && python3 scripts/agent_pull.py
```

### Diff (check for drift)

Compare local files against the live agent without changing anything:

```bash
source .env && python3 scripts/agent_pull.py --diff
```

---

## Rules

1. **Local files are the source of truth.** Make changes here, then push.
2. **Never edit the agent in the ElevenLabs dashboard** without pulling
   immediately afterwards — otherwise the next push will overwrite your
   dashboard changes.
3. **Commit after every push.** The git history becomes the audit trail.
4. The `system_prompt.md` file is **plain text only** — no YAML
   frontmatter, no metadata headers. The push script sends it verbatim.
5. When the target workflow is built, each subagent node's prompt
   override will live in `agent_config/nodes/<node_name>/prompt.md`
   and the push/pull scripts will be extended to sync workflow nodes.

# SimViva Data Architecture

## Design Principles

1. **Separate what is tested from how it is tested.** Scenarios (content) are format-agnostic. Exam formats are thin wrappers that slot scenarios in. When the FRCA restructures in July 2027, you add a new format file — the scenarios stay untouched.

2. **Verbal-only focus.** Every scenario models a spoken interaction: examiner asks, candidate talks. This works identically for traditional vivas, OSCE talking stations, and whatever CASE/FCPE turn out to be.

3. **Start with files, migrate to a database later.** JSON files validated against TypeScript types. No build step required. When you need multi-user persistence, the schema maps directly to Supabase/Firestore collections.

---

## Three-Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│  LAYER 3: TRACKING                                  │
│  Sessions, attempts, transcripts, mastery           │
│  (References content by ID — survives format changes)│
├─────────────────────────────────────────────────────┤
│  LAYER 2: FORMAT                                    │
│  Exam blueprints: structure, timing, slot rules     │
│  (Swappable — add new file when exams change)       │
├─────────────────────────────────────────────────────┤
│  LAYER 1: CONTENT                                   │
│  Scenarios, topics, key facts                       │
│  (Format-agnostic — never expires)                  │
└─────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
data/
├── README.md              ← You are here
├── schema.ts              ← TypeScript interfaces (source of truth)
├── topics.json            ← Curriculum topic taxonomy tree
├── formats/               ← Exam format definitions (one per format)
│   ├── primary_soe_2024.json
│   ├── final_soe1_2024.json
│   ├── primary_case_2027.json    ← Placeholder, fill when RCoA publishes
│   └── final_fcpe_2027.json      ← Placeholder, fill when RCoA publishes
└── scenarios/             ← Question bank (one file per scenario)
    ├── tracheostomy_management_001.json
    ├── tracheostomy_anatomy_001.json
    └── propofol_pharmacology_001.json
```

---

## Layer 1: Content

### Scenarios (`data/scenarios/*.json`)

The atomic content unit. One file = one examinable verbal block.

A scenario doesn't know which exam format it belongs to. It only knows:
- What to ask (`stem`, `prompts`)
- What good answers contain (`keyFacts`, `expectedKeyFacts`)
- How to rescue a struggling candidate (`rescuePrompt`)
- What each score looks like (`scoringGuidance`)
- Which curriculum topics it covers (`topicTagIds`)

**Key fields:**

| Field | Purpose |
|---|---|
| `id` | Unique identifier, e.g. `tracheostomy_management_001` |
| `domain` | Primary science domain (anatomy, pharmacology, etc.) |
| `topicTagIds` | References to `topics.json` — enables cross-cutting analytics |
| `stem` | Opening question. Use `{{surname}}` for personalisation |
| `prompts[]` | Ordered progression through Bloom's tiers |
| `prompts[].tier` | `recall` → `mechanism` → `application` → `synthesis` → `evaluation` |
| `prompts[].expectedKeyFacts` | What the candidate should cover for this specific prompt |
| `rescuePrompt` | ONE simplified alternative when the candidate is stuck |
| `keyFacts` | Master list across all prompts — used for scoring |
| `scoringGuidance` | RCoA per-question mark descriptors (pass/borderline/fail → 2/1/0) |
| `isActive` | Soft delete / draft control |

**Naming convention:** `{topic}_{type}_{number}.json`
- `tracheostomy_management_001.json` (clinical)
- `tracheostomy_anatomy_001.json` (science)
- `propofol_pharmacology_001.json` (pharmacology)

### Topics (`data/topics.json`)

Hierarchical taxonomy of curriculum concepts. **Not** tied to exam structure.

```
Anatomy (top level)
  └── Airway Anatomy
       └── Tracheostomy
       └── Laryngeal Anatomy
```

Scenarios reference topic IDs. Analytics roll up the tree — you can ask "how is this user doing at Airway Anatomy?" and it aggregates across all child topics.

**Adding a topic:** Append to the JSON array with a unique `id` and set `parentId` to the parent's `id` (or `null` for top-level).

---

## Layer 2: Format

### Exam Formats (`data/formats/*.json`)

Each file defines one exam structure: sections, slots, timing.

**Current formats:**

| File | Exam | Status |
|---|---|---|
| `primary_soe_2024.json` | Primary FRCA SOE | Active until June 2028 |
| `final_soe1_2024.json` | Final FRCA SOE1 | Active until June 2028 |
| `primary_case_2027.json` | Primary FRCA CASE | **Placeholder** — fill when RCoA publishes |
| `final_fcpe_2027.json` | Final FRCA FCPE | **Placeholder** — fill when RCoA publishes |

**Structure:**

```
ExamFormat
  └── sections[]          e.g. "Section A", "Section B"
       └── slots[]        e.g. "Clinical Scenario (7 min)", "Science Question (5 min)"
            ├── durationSec
            ├── slotType    "clinical" | "science" | "mixed" | "any"
            └── requiredDomain   (optional — constrain what content fills this slot)
```

**When the 2027 formats are announced:** Create or update the placeholder files with real sections/slots/timings. No schema change needed.

### Interaction Modes

| Mode | Description | Used by |
|---|---|---|
| `viva` | Traditional examiner asks, candidate answers | SOE (current) |
| `observed_discussion` | OSCE-style discussion with examiner or actor | Potentially CASE/FCPE |
| `structured_oral` | Hybrid: structured Q&A with defined stations | Potentially CASE/FCPE |

All three are verbal — SimViva simulates the talking component regardless of mode.

---

## Layer 3: Tracking

Defined in `schema.ts` but not stored as files — this layer lives in a database (or ElevenLabs API) when you add persistence.

**Key entities:**

| Entity | Purpose |
|---|---|
| `User` | Candidate profile, target exam date, preferences |
| `Session` | One practice sitting, linked to a format |
| `ScenarioAttempt` | One attempt at one scenario — transcript, timing, score |
| `TopicMastery` | Per-user, per-topic spaced repetition state |

**Critical design choice:** `ScenarioAttempt` is keyed to `scenarioId` (content), not to a station type (format). The `formatId` is metadata on the attempt. This means:

- "How has this user done on tracheostomy?" works across SOE, CASE, and FCPE
- Historical data survives a format change
- Spaced repetition operates on topics, not exam structures

---

## Compatibility with Current Webapp

The existing `scenarios.json` (consumed by `webapp/index.html`) uses this shape:

```json
{ "id": "...", "topic": "...", "opening": "...", "points": [...], "probes": [...], "facts": [...], "rescue": "..." }
```

Mapping to the new schema:

| Old field | New field |
|---|---|
| `topic` | `topicTagIds[0]` name, or derive from `domain` |
| `opening` | `stem` |
| `points` | Aggregate of `prompts[].expectedKeyFacts` |
| `probes` | `prompts[].text` |
| `facts` | `keyFacts` |
| `rescue` | `rescuePrompt` |

A small adapter function can transform new-format scenarios into the old shape for the ElevenLabs agent, so you can migrate content progressively without rewriting the webapp.

---

## Pairing Scenarios (Final SOE1)

The Final SOE1 pairs a clinical scenario with a linked science question in each short case. Pairing uses two fields on each scenario:

| Field | Purpose | Example |
|---|---|---|
| `caseId` | Groups partners together | `"tracheostomy_001"` |
| `slotType` | Which slot it fills | `"clinical"` or `"science"` |

Scenarios sharing a `caseId` belong together:

```
caseId: "tracheostomy_001"    caseId: "tracheostomy_001"    caseId: null
slotType: "clinical"          slotType: "science"           slotType: "any"
tracheostomy_management_001   tracheostomy_anatomy_001      propofol_pharmacology_001
         ↕ paired ↕                                         (standalone)
```

Blueprint assembly: *find all scenarios with caseId X → put the clinical one in slot 0, the science one in slot 1.*

Standalone scenarios (`caseId: null`, `slotType: "any"`) work in Primary format or training mode where pairing doesn't apply.

---

## Quality Review

`ScenarioReview` in `schema.ts` defines how AI or humans grade the **scenarios themselves** (not candidate performance). Use this to:

- Flag outdated content after guideline changes
- Score prompt progression quality
- Identify scenarios that need rewriting
- Track which references have been checked

---

## How to Add Content

### Adding a new scenario

1. Create `data/scenarios/{topic}_{type}_{number}.json`
2. Follow the `Scenario` interface in `schema.ts`
3. Reference existing `topicTagIds` from `topics.json` (or add new ones)
4. Include prompts that escalate through Bloom's tiers
5. Write `scoringGuidance` for all 4 RCoA levels
6. Set `isActive: true` when ready for use

### Adding a new topic

1. Add to `data/topics.json` with a unique `id`
2. Set `parentId` to place it in the hierarchy
3. Reference from scenarios via `topicTagIds`

### Adding a new exam format (July 2027)

1. Update `data/formats/primary_case_2027.json` or `final_fcpe_2027.json`
2. Fill in real sections, slots, and timings from RCoA publications
3. Existing scenarios slot in without modification
4. Update the webapp to read the new format for session structure

---

## Future: Database Migration

When moving from JSON files to a database:

| JSON file | Database table/collection |
|---|---|
| `scenarios/*.json` | `scenarios` |
| `topics.json` | `topic_tags` |
| `formats/*.json` | `exam_formats` |
| (in-memory) | `users`, `sessions`, `scenario_attempts`, `topic_mastery` |

The schema in `schema.ts` maps 1:1 to database schemas. No structural changes needed.

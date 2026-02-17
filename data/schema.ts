/**
 * SimViva — Question Bank Data Schema
 *
 * Three-layer architecture:
 *   1. CONTENT  — Scenarios, topics, key facts (format-agnostic, never expires)
 *   2. FORMAT   — Exam blueprints defining structure/timing (swappable when exams change)
 *   3. TRACKING — Attempts, transcripts, mastery (references content by ID, survives format changes)
 *
 * Focused on the VERBAL/TALKING component only — works for:
 *   - Traditional viva (SOE)
 *   - OSCE talking stations
 *   - Combo formats (CASE 2027, FCPE 2027)
 *   - Any future oral assessment format
 *
 * Designed to survive the July 2027 FRCA exam restructure.
 * The curriculum is unchanged — only the exam wrapper changes.
 */

// ═══════════════════════════════════════════════════════════════
// LAYER 1: CONTENT — What is being tested
// ═══════════════════════════════════════════════════════════════

/**
 * Bloom's-style question progression tiers.
 * Maps to the SPEC.md 5-level progression.
 */
export type PromptTier =
  | "recall"       // 1. Define/Describe
  | "mechanism"    // 2. Explain mechanism
  | "application"  // 3. Apply to clinical scenario
  | "synthesis"    // 4. Troubleshoot/Problem-solve
  | "evaluation";  // 5. Justify decision

/**
 * The domain of knowledge a scenario tests.
 * These are curriculum domains — they don't change when the exam format changes.
 */
export type ScienceDomain =
  | "anatomy"
  | "physiology"
  | "pharmacology"
  | "physics"
  | "clinical_measurement"
  | "equipment"
  | "critical_care"
  | "pain_medicine"
  | "obstetric_anaesthesia"
  | "paediatric_anaesthesia"
  | "neuroanaesthesia"
  | "cardiothoracic"
  | "regional_anaesthesia"
  | "general_principles";

/**
 * A single examiner prompt within a scenario.
 */
export interface Prompt {
  /** Which Bloom's tier this prompt targets */
  tier: PromptTier;
  /** The examiner's words */
  text: string;
  /** Key facts the candidate should cover in response to THIS prompt */
  expectedKeyFacts: string[];
  /** Suggested time budget in seconds (advisory, not enforced) */
  timeBudgetSec?: number;
}

/**
 * A Scenario is the atomic content unit — one examinable verbal block.
 *
 * Format-agnostic: a scenario doesn't know if it's in a viva, OSCE, or CASE station.
 * It just knows what to ask, what good answers look like, and how to rescue.
 *
 * Compatible with the existing webapp's scenarios.json shape:
 *   { id, topic, opening, points, probes, facts, rescue }
 * mapped as:
 *   opening → stem, points → prompts[].expectedKeyFacts,
 *   probes → prompts[].text, facts → keyFacts, rescue → rescuePrompt
 *
 * Template variable: Use {{candidate_name}} in stems for the candidate's surname.
 * This matches the ElevenLabs agent's dynamic variable naming convention.
 */

/**
 * Records the governance and audit trail for AI-generated content.
 * Complies with the SimViva AI Governance Framework (docs/AI_GOVERNANCE.md).
 */
export interface AIProvenance {
  /** The specific model version used for generation (e.g., "Claude-3-Sonnet-20240229") */
  generatedBy: string;
  /** ISO 8601 timestamp of generation */
  generatedAt: string;
  /** Version identifier of the system prompt used */
  promptVersion: string;
  /** 
   * List of unique identifiers for source material (e.g., "BJA_Sepsis_2023").
   * Ensures the "Factual Firewall" principle: facts are extracted, expression is generated.
   */
  sourceMaterial: string[];
  
  /**
   * Quality Assurance Record based on the ACI Framework (Kung et al., 2023).
   * All content must pass human verification before release.
   */
  validation: {
    /** Full name or ID of the qualified human reviewer (FRCA or equivalent) */
    reviewedBy: string;
    /** ISO 8601 timestamp of review */
    reviewedAt: string;
    /** Current governance status */
    status: 'draft' | 'pending_review' | 'approved' | 'rejected';
    
    // Quality Metrics (0.0 - 1.0 Scale)
    /** 
     * accuracy: Correctness of medical facts. MUST begin with 1.0 for approval.
     * Any inaccuracy is an immediate hard fail.
     */
    accuracy?: number;
    /** concordance: Logical consistency between stem, prompt, and key facts. Target > 0.9 */
    concordance?: number;
    /** insight: Educational value / "novelty" of the clinical reasoning. Target > 0.75 */
    insight?: number;
    
    /** Specific notes on required remediation or approval justification */
    notes?: string;
  };
}

export interface Scenario {
  /** Unique ID, e.g. "tracheostomy_management_001" */
  id: string;

  /** ISO 8601 timestamp — tracks content freshness without full versioning overhead */
  updatedAt: string;

  // ── Ethical / Source Tracking ──
  provenance?: AIProvenance;

  // ── Demographic Monitoring (EU AI Act Art. 10 Bias Control) ──
  demographics?: {
    patientAgeGroup: 'neonate' | 'infant' | 'child' | 'adolescent' | 'adult' | 'geriatric';
    patientGender: 'male' | 'female'; 
  };

  // ── What it covers ──

  /** Primary science domain */
  domain: ScienceDomain;
  /** References to TopicTag IDs — enables cross-cutting analytics */
  topicTagIds: string[];

  // ── Pairing ──

  /**
   * Groups scenarios that belong together (e.g. clinical + science pair).
   * Scenarios sharing a caseId are compatible partners.
   * null = standalone scenario, no pairing needed.
   *
   * Example: caseId "tracheostomy_001" links the management + anatomy scenarios.
   */
  caseId: string | null;
  /**
   * What kind of exam slot this scenario fills.
   * Used by blueprint assembly to put the right scenario in the right slot.
   *   clinical = 7-min scenario (Final SOE1)
   *   science  = 5-min linked question (Final SOE1)
   *   any      = standalone / Primary (fills any slot)
   */
  slotType: "clinical" | "science" | "any";
  /**
   * Ordering within a case group (scenarios sharing the same caseId).
   *   0 = unordered — can appear in any position within the case
   *   1,2,3... = must appear in this sequence
   *
   * Assembly rule: serve numbered phases in order first,
   * then scatter 0s into remaining slots.
   *
   * Ignored when caseId is null (standalone scenarios).
   */
  caseOrder: number;

  // ── The content ──

  /** Opening question the examiner reads out */
  stem: string;
  /**
   * Ordered prompts — examiner works through these in sequence.
   * Tiers should escalate (recall → mechanism → application → synthesis → evaluation)
   * but not every scenario needs all 5 tiers.
   */
  prompts: Prompt[];
  /** ONE simplified alternative if the candidate is struggling */
  rescuePrompt: string;
  /** Master list of all key facts across all prompts — used for scoring */
  keyFacts: string[];

  // ── Scoring guidance ──

  /** What each RCoA score looks like for THIS scenario */
  scoringGuidance: {
    /** 4 = Pass+ */
    pass_plus: string;
    /** 3 = Pass */
    pass: string;
    /** 2 = Borderline */
    borderline: string;
    /** 1 = Fail */
    fail: string;
  };

  // ── Metadata ──

  /** Free-text author attribution */
  author?: string;
  /** URLs for candidate further reading — BJA Education, textbooks, guidelines */
  furtherReading?: string[];
  /** Soft-delete / draft control */
  isActive: boolean;
}

/**
 * Hierarchical topic taxonomy — curriculum-based, not exam-based.
 *
 * Examples:
 *   { id: "airway", name: "Airway Management", parentId: null }
 *   { id: "tracheostomy", name: "Tracheostomy", parentId: "airway" }
 *   { id: "trach_anatomy", name: "Tracheostomy Anatomy", parentId: "tracheostomy" }
 *
 * Scenarios reference these by ID. Analytics roll up the tree.
 */
export interface TopicTag {
  id: string;
  name: string;
  /** null = top-level domain */
  parentId: string | null;
  /** RCoA curriculum reference code if applicable */
  rcoaCurriculumRef?: string;
}

// ═══════════════════════════════════════════════════════════════
// LAYER 2: FORMAT — How the exam is structured
// ═══════════════════════════════════════════════════════════════

/**
 * How the verbal interaction happens.
 * All values involve the candidate TALKING — this is what SimViva simulates.
 */
export type InteractionMode =
  | "viva"                 // Traditional: examiner asks, candidate answers verbally
  | "observed_discussion"  // OSCE-style: candidate discusses with examiner/actor
  | "structured_oral";     // Hybrid: structured Q&A with defined stations

/**
 * A single slot within an exam section — one timed verbal block.
 */
export interface FormatSlot {
  /** Label for display, e.g. "Clinical Scenario", "Science Question", "Topic 1" */
  label: string;
  /** Duration in seconds */
  durationSec: number;
  /** What kind of content fills this slot */
  slotType: "clinical" | "science" | "mixed" | "any";
  /** If science, which domain should fill this slot (null = any) */
  requiredDomain?: ScienceDomain;
}

/**
 * A group of slots examined together, e.g. "Short Case 1" or "Examiner 1 block".
 */
export interface FormatSection {
  /** e.g. "Short Case 1", "Examiner 1" */
  label: string;
  /** Ordered slots within this section */
  slots: FormatSlot[];
  /** Changeover time between sections in seconds */
  changeoverSec?: number;
}

/**
 * A complete exam format definition — stored as data, not code.
 *
 * When the FRCA restructures in July 2027, you add a new ExamFormat record.
 * No schema migration, no code change. The app reads the active format at runtime.
 *
 * Current formats:
 *   - primary_soe_2024: 2 examiners × 2 topics × 4 min
 *   - final_soe1_2024:  2 sections × 2 short cases × (7 min clinical + 5 min science)
 *
 * Future formats (add when RCoA publishes details):
 *   - primary_case_2027: TBD station circuit
 *   - final_fcpe_2027:   TBD station circuit
 */
export interface ExamFormat {
  /** Unique ID, e.g. "final_soe1_2024" */
  id: string;
  /** Human-readable name */
  name: string;
  /** When this format is/was in effect */
  validFrom: string;
  /** null = still current */
  validUntil: string | null;
  /** How the verbal interaction works */
  interactionMode: InteractionMode;
  /** Top-level sections, e.g. "Section A" and "Section B" */
  sections: FormatSection[];
  /** Total exam duration in seconds (sum of all slots + changeovers) */
  totalDurationSec: number;
  /** Notes about this format for content authors */
  notes?: string;
}

/**
 * An assembled exam — a specific set of scenarios slotted into a format.
 *
 * Think of ExamFormat as the template and ExamBlueprint as the filled-in instance.
 * The blueprint enforces coverage rules (diverse domains, no duplicate topics).
 */
export interface ExamBlueprint {
  id: string;
  formatId: string;
  createdAt: string;
  generatedBy: "human" | "ai";

  /**
   * Maps format slots to scenarios.
   * Key: "sectionIndex.slotIndex" (e.g. "0.0" = first section, first slot)
   * Value: scenario ID
   */
  slotAssignments: Record<string, string>;

  /** Derived: which science domains are covered — for coverage validation */
  domainsCovered: ScienceDomain[];
  /** Derived: which topic tags are covered */
  topicTagsCovered: string[];
}

// ═══════════════════════════════════════════════════════════════
// LAYER 3: TRACKING — How the user is doing
// ═══════════════════════════════════════════════════════════════

export type Score = 1 | 2 | 3 | 4;

export interface User {
  id: string;
  createdAt: string;
  surname: string;
  /** Which exam they're preparing for — drives scenario selection */
  targetExam: string;
  /** Drives spaced repetition urgency */
  targetExamDate?: string;
  preferences: {
    sessionLengthMin: number;
    mode: "exam" | "training";
    voiceId?: string;
  };
}

/**
 * One practice session — a single sitting.
 */
export interface Session {
  id: string;
  userId: string;
  startedAt: string;
  endedAt?: string;
  /** Which exam format was used */
  formatId: string;
  /** Which blueprint was used (if pre-assembled) */
  blueprintId?: string;
  mode: "exam" | "training";
  durationSec: number;
  /** ElevenLabs conversation ID — links to their API for audio/analysis retrieval */
  elevenLabsConversationId?: string;
}

/**
 * One attempt at one scenario within a session.
 * This is where the real data lives — transcript, timing, score.
 *
 * Keyed to scenarioId (content), not to a station type (format).
 * This means you can query "how has this user done on tracheostomy scenarios"
 * regardless of whether they sat them in SOE, CASE, or FCPE format.
 */
export interface ScenarioAttempt {
  id: string;
  sessionId: string;
  scenarioId: string;
  /** Which format this was sat in — metadata, not the primary key */
  formatId: string;
  /** Position in the exam: "0.0" = Section A, Short Case 1, Clinical */
  formatSlotRef?: string;

  // ── Raw capture ──

  transcript: TranscriptEntry[];
  /** Cloud storage URL for the audio recording */
  audioUrl?: string;
  durationSec: number;

  // ── Timing analytics ──

  silencePeriods: SilencePeriod[];
  interruptionCount: number;
  rescueUsed: boolean;
  /** How far through the prompt progression they got */
  promptTiersReached: PromptTier[];

  // ── Scoring ──

  score: Score;
  keyFactsCovered: string[];
  keyFactsMissed: string[];

  // ── AI feedback ──

  feedback: {
    summary: string;
    strengths: string[];
    improvements: string[];
    suggestedResources: string[];
    /** AI's confidence in its own grading (0-1) — flag low-confidence for human review */
    confidence: number;
  };

  /** Topic tags from the scenario — denormalised for fast queries */
  topicTagIds: string[];
}

export interface TranscriptEntry {
  speaker: "examiner" | "candidate" | "system";
  text: string;
  /** Seconds from start of this scenario attempt */
  startSec: number;
  endSec: number;
  /** Which prompt tier was active when this was spoken */
  promptTier?: PromptTier;
  /** Special events overlaid on the transcript */
  event?: "silence_prompt" | "interruption" | "rescue" | "time_warning" | "time_end" | "handover";
}

export interface SilencePeriod {
  startSec: number;
  durationSec: number;
  /** Did it cross the 5-7s threshold and trigger an examiner prompt? */
  triggeredPrompt: boolean;
}

/**
 * Per-user, per-topic mastery state — drives spaced repetition.
 * One record per (userId, topicTagId) pair.
 */
export interface TopicMastery {
  userId: string;
  topicTagId: string;

  /** SM-2 algorithm fields */
  easeFactor: number;
  intervalDays: number;
  nextReviewDate: string;
  repetitionCount: number;

  /** Rolling history for trend calculation */
  history: {
    attemptId: string;
    score: Score;
    date: string;
  }[];

  averageScore: number;
  trend: "improving" | "stable" | "declining";
  lastAttemptDate: string;
}

// ═══════════════════════════════════════════════════════════════
// QUALITY REVIEW — AI or human grading of the scenarios themselves
// ═══════════════════════════════════════════════════════════════

/**
 * A review of a scenario's quality — not a candidate's performance.
 * Used for maintaining and improving the question bank.
 */
export interface ScenarioReview {
  scenarioId: string;
  reviewedAt: string;
  reviewerType: "ai" | "human";
  reviewerId: string;

  /** All scores 1-5 */
  clarity: number;
  clinicalRelevance: number;
  curriculumAlignment: number;
  guidelineCurrentness: number;
  difficultyCalibration: number;
  promptProgression: number;

  flaggedIssues: string[];
  suggestedEdits: string[];
  referencesChecked: string[];
}

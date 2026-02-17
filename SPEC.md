# FRCA Viva AI Voice Practice App — Full Spec

Goal: Most realistic FRCA viva simulation — ElevenLabs voice agents + workflows for Monday PoC, with path to full PWA.

Target: Primary and Final FRCA SOE candidates.

## Exam Structure
- Primary SOE 1 (morning, 30 min): Examiner A = Pharmacology (3×5 min), Examiner B = Physiology (3×5 min)
- Primary SOE 2 (afternoon, 30 min): Examiner C = Clinical Anaesthesia (3×5 min), Examiner D = Physics/CM/Equipment/Safety (3×5 min)
- Final: SOE1 (clinical subspecialties), SOE2 (clinical scenarios + critical incidents)

## Question Progression
1. Define/Describe (factual recall)
2. Explain mechanism (understanding)
3. Apply to clinical scenario (application)
4. Troubleshoot/Problem-solve (synthesis)
5. Justify decision (evaluation)

## Examiner Persona Rules
- Never say "correct," "good," "well done," "exactly right"
- Never say "wrong" or "incorrect" explicitly
- Neutral acknowledgments only: "I see," "Mm-hmm," "Go on"
- Consistent tone regardless of answer quality
- "Are you sure?" on both correct AND incorrect answers (~30%)
- Probe: "Why?" and "What else?" after substantive answers
- Move on without explanation when time expires
- Interrupt verbose/off-topic after 20-30 seconds
- 5-7 seconds silence before prompting
- Formal: "Dr. [Surname], could you explain..."

## Timing
- 5-minute blocks per topic question (matching real exam)
- Warning at 4:30, end at 5:00 (hard transition)
- Total SOE part: 30 minutes (2 examiners × 15 minutes)

## Silence Protocol
- 0-3s: Wait silently
- 3-5s: Continue waiting (pressure builds)
- 5-7s: "What else can you add?"
- 7-10s: "Let's move on..." or "Perhaps you could tell me about..."
- >10s: Definitive topic change

## Interruption
Triggers: verbose >30s, off-topic, repetition, time expiring, candidate seeks confirmation
Phrases: "That's fine. Let's move on...", "Coming back to the case...", "Let me stop you there..."
Rescue: ONE simplified alternative, same neutral tone, then move on

## Scoring (RCoA SOE Marking)
Per-question: fail (0) / borderline (1) / pass (2)
All 4 examiners mark all 6 questions independently in their SOE part.
Total: 48 marks, pass threshold: 37.

## Post-Session Feedback
- Score per topic
- Key points covered/missed
- Specific improvement feedback
- BJA Education article links
- Comparison to previous attempts

## Learning Science
- Spaced repetition: irregular intervals outperform fixed schedules
- Testing effect > restudying
- Transfer-appropriate processing: voice-to-voice practice matches exam format

## Open Questions
1. Training mode vs exam-only?
2. Content licensing / BJA partnership?
3. Monetisation model?
4. Stress metrics as anxiety indicators?

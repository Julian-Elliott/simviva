# Gold Standard Question Bank

## Overview

This directory contains a curated bank of 21 high-quality viva scenarios designed for the SimViva FRCA examination simulator. Each scenario represents a "gold standard" question that embodies best practices in medical education assessment.

## Quality Standards

All scenarios in this bank meet the following criteria:

### 1. **Clinical Accuracy**
- Content derived from authoritative sources (BJA Education, RCoA curriculum, NICE/AAGBI guidelines)
- Reflects current best practice as of 2026
- Awaiting clinical reviewer sign-off per AI Governance Framework

### 2. **Educational Design**
- **Bloom's Taxonomy Progression**: Questions escalate through 5 cognitive levels
  - Recall: Define/Describe facts
  - Mechanism: Explain underlying principles
  - Application: Apply to clinical scenarios
  - Synthesis: Troubleshoot/Problem-solve
  - Evaluation: Justify decisions, compare approaches

### 3. **Examination Alignment**
- **RCoA Marking Scheme**: Each scenario includes pass/borderline/fail descriptors matching the real Primary FRCA SOE 0/1/2 scale
- **Realistic Pacing**: Time budgets guide 5-7 minute topic blocks
- **Rescue Prompts**: One simplified alternative for struggling candidates

### 4. **AI Governance Compliance**
- Full provenance tracking (model, prompt version, source material)
- Transparency about AI generation
- Human review required before activation (currently all pending_review)
- Demographic representation (gender, age group) tracked

## Coverage Map

### Primary FRCA SOE 1 (Pharmacology & Physiology)

| Domain | Count | Topics Covered |
|--------|-------|----------------|
| **Pharmacology** | 6 | Propofol, Remifentanil, Suxamethonium, Local Anaesthetics, Sevoflurane, Antiemetics |
| **Physiology** | 4 | Oxygen Cascade, Cardiac Action Potential, Renal Physiology, Acid-Base |

### Primary FRCA SOE 2 (Clinical & Physics)

| Domain | Count | Topics Covered |
|--------|-------|----------------|
| **Clinical Anaesthesia** | 5 | Difficult Airway, Anaphylaxis, Obstetric Haemorrhage, Spinal Anaesthesia, Tracheostomy |
| **Physics/Equipment** | 3 | Pulse Oximetry, Capnography, Vaporizers |
| **Critical Care** | 2 | Sepsis, Mechanical Ventilation |
| **Anatomy** | 1 | Tracheostomy Anatomy |

## Usage Notes

### For Content Developers
- Follow the established schema in `data/schema.ts`
- Use naming convention: `{topic}_{type}_{number}.json`
- Ensure `isActive: false` until clinical review complete
- Include source material citations for audit trail

### For Examiners (AI Agents)
- Scenarios are injected as dynamic variables at session start
- Follow the neutral examiner persona (see `agent_config/system_prompt.md`)
- Use `rescuePrompt` if candidate struggles persistently
- Mark using `scoringGuidance` descriptors (0/1/2 scale)

### For Candidates
- Each scenario represents a realistic 5-7 minute viva topic
- Expect progressive difficulty through Bloom's tiers
- Comprehensive answers should cover most `keyFacts`
- Feedback references `expectedKeyFacts` from each prompt

## Expansion Roadmap

**Next Phase (Target: 50 scenarios)**
- Final FRCA topics (subspecialty anaesthesia)
- Paired cases for Final SOE1 format (clinical + linked science)
- OSCE talking stations
- Critical incident scenarios

**Long-term (Target: 200+ scenarios)**
- Full curriculum coverage across all RCoA domains
- Multiple variants per topic for spaced repetition
- Adaptive difficulty based on user performance history

## Validation Checklist

Before activating a scenario (`isActive: true`):

- [ ] Clinical accuracy verified by FRCA-qualified reviewer
- [ ] Source material citations checked
- [ ] Bloom's progression validated (no tier skips, logical flow)
- [ ] Scoring descriptors calibrated against real exam standards
- [ ] Demographics logged (for bias monitoring)
- [ ] Provenance metadata complete
- [ ] JSON syntax validated
- [ ] Tested in live agent conversation

## References

- **RCoA Primary FRCA Curriculum (2021)**: https://rcoa.ac.uk/training-careers/training-anaesthesia/curricula
- **BJA Education**: https://e-safe-anaesthesia.org
- **AI Governance Framework**: See `docs/AI_GOVERNANCE.md`
- **Data Architecture**: See `data/README.md`

---

**Status**: 21 scenarios | 18 new + 3 existing | All pending clinical review  
**Last Updated**: 2026-02-18  
**Governance Compliance**: ✅ EU AI Act Article 50 (Transparency), Article 14 (Human Oversight)

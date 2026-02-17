# AI Governance & Content Integrity Framework

**Version:** 1.0  
**Effective Date:** 17 February 2026  
**Status:** Active Policy
**Compliance:** EU AI Act (Regulation 2024/1689), GDPR, UK Data Protection Act 2018

## 1. Executive Summary

SimViva utilises generative artificial intelligence (AI) to scale the production of postgraduate medical education content (FRCA). To ensure clinical safety, educational validity, and strict adherence to intellectual property laws, all AI-generated content is subject to this Governance Framework.

This framework mandates a **"Human-in-the-Loop" (HITL)** architecture where AI is utilised solely as a drafting tool, with final authority and liability vesting in qualified human reviewers. It is designed to comply with the **EU AI Act**, specifically addressing obligations for High-Risk AI Systems in education (Annex III) and General Purpose AI transparency (Article 50).

---

## 2. Regulatory Alignment (EU AI Act)

Although SimViva is a formative assessment tool (practice) rather than a summative certification authority (like the RCoA), we adopt a "High-Risk" compliance posture to ensure maximum safety.

| EU AI Act Article | SimViva Control Measure |
| :--- | :--- |
| **Art. 14 (Human Oversight)** | "Human-in-the-Loop" (HITL) architecture. No content is released without manual review by an FRCA-qualified human. |
| **Art. 15 (Accuracy)** | Adoption of the **ACI Protocol** (Kung et al.) with a 100% accuracy mandate for medical facts. |
| **Art. 50 (Transparency)** | Users are explicitly notified of AI usage ("AI-Drafted, Human-Verified"). |
| **Art. 53 (Copyright)** | The "Factual Firewall" ensures generated content respects EU copyright directive by isolating facts from expression. |

---

## 3. Intellectual Property Compliance: The "Factual Firewall"

To prevent the generation of derivative works that infringe upon third-party copyright (e.g., BJA Education, Oxford University Press), SimViva employs a strict segregation of duties in the content generation pipeline.

### 3.1. Principle of Atomic Fact Extraction
Copyright law (EU, UK, US) protects *expression*, not *facts*.
*   **Protocol**: Source material is never provided directly to the generation model. 
*   **Process**: A distinct "Extraction Phase" isolates atomic medical facts (e.g., pharmacokinetics, guideline thresholds) from their original literary expression.
*   **Audit**: These atomic facts form the only input for the generation phase, complying with **Article 53 (Copyright)** obligations for General Purpose AI models.

### 3.2. The Clean-Room Generation Pipeline
1.  **Input**: Anonymized, unstructured lists of atomic facts.
2.  **Generation**: The AI model ("The Architect") constructs a *new, original* clinical scenario and viva structure based solely on the provided facts.
3.  **Output**: A unique expression of public domain medical knowledge.

---

## 4. Clinical Safety Assurance: The ACI Protocol (Art. 15 Compliance)

All AI-drafted content must undergo rigorous human validation before release. We adopt the **ACI Framework** (Kung et al., *PLOS Digital Health* 2023) as our standard for acceptance criteria, satisfying **Article 15 (Cybersecurity & Robustness)** requirements for accuracy during the lifecycle of the AI system.

Every scenario must be scored by a qualified reviewer (FRCA or equivalent) against three dimensions:

| Dimension | Definition | Acceptance Threshold |
| :--- | :--- | :--- |
| **Accuracy** | Correctness of medical facts against established guidelines. | **100% (Binary Pass/Fail)** |
| **Concordance** | Logical consistency between the question, answer, and explanation. | **> 90%** |
| **Insight** | Educational value; presence of "novel or non-obvious" learning points. | **> 75%** |

*   *Any content failing the Accuracy check is immediately rejected and flagged for root cause analysis.*

---

## 5. Data Lineage & Provenance (Art. 13 & 50)

To satisfy audit requirements under **Article 13 (Technical Documentation)**, all content artifacts maintain a complete "Chain of Custody" record within their metadata manifest.

### 5.1. Metadata Schema
The `AIProvenance` record (defined in `data/schema.ts`) acts as our technical documentation log, tracking:
*   **Generator ID**: Specific model version (e.g., `Claude-3.5-Sonnet-20240620`).
*   **Prompt Version**: A link to the version-controlled system prompt file (e.g., `data/system_prompts/architect_v1.0.0.md`). This enables exact reconstruction of the AI's instructions.
*   **Source Material**: References to the primary literature from which facts were extracted.
*   **Reviewer Chain**: The digital signature of the human approver.

### 5.2. Auditability
*   **Traceability**: Given a specific scenario ID, an auditor can trace back to the specific source guidelines used and the specific human who authorized its release.
*   **Immutability**: Once approved, the `provenance` block is locked. Any subsequent edits require a new version or re-validation.

---

## 6. Ethical Standards & Bias Mitigation (Art. 10 & 26)

### 6.1. Demographic Neutrality (Art. 10)
SimViva enforces **data-driven bias monitoring** rather than relying solely on subjective review.
*   **Infrastructure**: All scenarios must contain a structured `demographics` object (`patientAgeGroup`, `patientGender`).
*   **Monitoring**: We maintain a live distribution report to ensure the question bank reflects the diversity of the UK patient population (e.g., 50/50 gender balance, appropriate age curves).
*   **Audit**: An auditor can instantaneously query the demographic spread of the entire content library.

### 6.2. Transparency (Art. 50 & 52)
*   **User Disclosure**: End-users are explicitly informed that content is "AI-Drafted, Human-Verified," meeting the transparency obligations for AI systems interacting with natural persons.
*   **Limitation of Liability**: While every effort is made to ensure accuracy, SimViva maintains that this is a *supplementary* educational tool.

---

## 7. Incident Management (Post-Market Monitoring - Art. 61)

In compliance with **Article 61 (Post-Market Monitoring)**, SimViva maintains a system for collecting and analyzing performance data throughout the AI system's lifetime.

1.  **Immediate Kill Switch**: Users can flag content as inaccurate. This triggers an immediate `isActive: false` state.
2.  **Root Cause Analysis**: The `provenance` log is analyzed to determine if the error originated from:
    *   Incorrect Fact Extraction (human/process error).
    *   Model Hallucination (AI error).
    *   Reviewer Oversight (human error).
3.  **Remediation**: Corrective action is taken before the content is re-enabled.

---
# AI Governance & Content Integrity Framework

**Version:** 1.0  
**Effective Date:** 17 February 2026  
**Status:** Active Policy

## 1. Executive Summary

SimViva utilizes generative artificial intelligence (AI) to scale the production of postgraduate medical education content (FRCA). To ensure clinical safety, educational validity, and strict adherence to intellectual property laws, all AI-generated content is subject to this Governance Framework.

This framework mandates a **"Human-in-the-Loop" (HITL)** architecture where AI is utilised solely as a drafting tool, with final authority and liability vesting in qualified human reviewers.

---

## 2. Intellectual Property Compliance: The "Factual Firewall"

To prevent the generation of derivative works that infringe upon third-party copyright (e.g., BJA Education, Oxford University Press), SimViva employs a strict segregation of duties in the content generation pipeline.

### 2.1. Principle of Atomic Fact Extraction
Copyright law protects *expression*, not *facts*. 
*   **Protocol**: Source material is never provided directly to the generation model. 
*   **Process**: A distinct "Extraction Phase" isolates atomic medical facts (e.g., pharmacokinetics, guideline thresholds) from their original literary expression.
*   **Audit**: These atomic facts form the only input for the generation phase.

### 2.2. The Clean-Room Generation Pipeline
1.  **Input**: Anonymized, unstructured lists of atomic facts.
2.  **Generation**: The AI model ("The Architect") constructs a *new, original* clinical scenario and viva structure based solely on the provided facts.
3.  **Output**: A unique expression of public domain medical knowledge.

---

## 3. Clinical Safety Assurance: The ACI Protocol

All AI-drafted content must undergo rigorous human validation before release. We adopt the **ACI Framework** (Kung et al., *PLOS Digital Health* 2023) as our standard for acceptance criteria.

Every scenario must be scored by a qualified reviewer (FRCA or equivalent) against three dimensions:

| Dimension | Definition | Acceptance Threshold |
| :--- | :--- | :--- |
| **Accuracy** | Correctness of medical facts against established guidelines. | **100% (Binary Pass/Fail)** |
| **Concordance** | Logical consistency between the question, answer, and explanation. | **> 90%** |
| **Insight** | Educational value; presence of "novel or non-obvious" learning points. | **> 75%** |

*   *Any content failing the Accuracy check is immediately rejected and flagged for root cause analysis.*

---

## 4. Data Lineage & Provenance

To satisfy audit requirements, all content artifacts maintain a complete "Chain of Custody" record within their metadata manifest.

### 4.1. Metadata Schema
The `AIProvenance` record (defined in `data/schema.ts`) tracks:
*   **Generator ID**: Specific model version (e.g., `Claude-3.5-Sonnet-20240620`) to trace regression issues.
*   **Prompt Version**: The governance-approved system prompt used for generation.
*   **Source Material**: References to the primary literature from which facts were extracted (e.g., `BJA_Sepsis_2023`).
*   **Reviewer Chain**: The digital signature of the human approver.

### 4.2. Auditability
*   **Traceability**: Given a specific scenario ID, an auditor can trace back to the specific source guidelines used and the specific human who authorized its release.
*   **Immutability**: Once approved, the `provenance` block is locked. Any subsequent edits require a new version or re-validation.

---

## 5. Ethical Standards & Bias Mitigation

### 5.1. Demographic Neutrality
Reviewers are mandated to screen scenarios for:
*   Stereotypical patient representations based on race, gender, or age.
*   Unjustified associations between demographics and pathology (unless medically evidentiary).

### 5.2. Transparency
*   **User Disclosure**: End-users are explicitly informed that content is "AI-Drafted, Human-Verified."
*   **Limitation of Lability**: While every effort is made to ensure accuracy, SimViva maintains that this is a *supplementary* educational tool, not a replacement for primary clinical guidelines.

---

## 6. Incident Management

In the event of a reported clinical error in live content:
1.  **Immediate Kill Switch**: The content is disabled via the `isActive: false` flag.
2.  **Root Cause Analysis**: The `provenance` log is analyzed to determine if the error originated from:
    *   Incorrect Fact Extraction (human/process error).
    *   Model Hallucination (AI error).
    *   Reviewer Oversight (human error).
3.  **Remediation**: Corrective action is taken before the content is re-enabled.

---

**Approved By:**  
*SimViva Clinical Governance Committee*

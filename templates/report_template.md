# Deep Reading Report: <Paper Title>

Use this template together with `traceability_manifest.json` and `research_lens.json`.
Write the final report in Chinese when the user's current request is primarily in Chinese; keep proper nouns, fixed technical identifiers, claim IDs, filenames, and JSON keys in English. Otherwise write the report in English.
This report is the main teaching artifact, not a short summary.
Do not impose an artificial length limit.
Write enough detail that a reader can understand the original paper's motivation, method, formulas, experiments, evidence strength, limitations, and future directions from this report alone.
For every numbered section below:

- start with `### Anchored Points`
- add one or more claims in the exact form `- [C<section>.<index>] claim text`
- make sure every claim ID appears in `traceability_manifest.json`
- if a claim is reconstructive rather than directly stated, mark it as inferential in the manifest
- if one claim depends on multiple source locations, list every materially necessary source location as separate evidence rows in `traceability_manifest.json`
- if one bullet contains multiple independent claims, split it into multiple claim IDs before writing the manifest
- after the anchored points, add the longer explanation, tables, formulas, critique, or author-side reconstruction as needed
- do not leave a section as only a short anchored-claim list; add self-contained explanatory prose after the claims
- preserve important equations, figures, tables, ablations, datasets, baselines, hyperparameters, and implementation details when the source provides them
- prefer comprehensive grounded explanation over brevity unless the user explicitly asks for a concise version

## 1. Paper Identification and Source Package Used
## 2. One-Sentence Thesis and Research Equation
## 3. Title Interpretation
## 4. What Problem the Paper Really Solves
## 5. Scientific Problem Ladder
## 6. How the Authors May Have Found This Direction
## 7. How the Authors Built the Story
## 8. Related Work, Key Citations, and What Was Still Missing
## 9. Main Idea
## 10. Symbols, Concepts, and Notation
## 11. Key Formulas and Equation-by-Equation Explanation
## 12. Theory, Proof, and Practice Mapping
## 13. Algorithm / Module Walkthrough with Concrete Example
## 14. Method Deep Reading: The Author-Thinking Behind Each Module
## 15. Figure Explanations (PDF and/or LaTeX)
## 16. Experimental Design
## 17. Experiments as Story Evidence and Claim Alignment Audit
## 18. Reviewer-Lens Audit
## 19. Innovation Points and Claim-by-Claim Support Audit
## 20. Story-Making Pattern Worth Learning
## 21. Weaknesses, Limitations, and Improvement Room
## 22. Innovation Type and Boundary Judgment
## 23. Future Directions and Boundary-Pushing Ideas
## 24. Simple Vivid Story Summary
## 25. Sources Used

---

## Optional Structured Aids for `research_lens.json`

### Research Equation
- old success / popular paradigm:
- broken assumption:
- hard setting or realistic constraint:
- borrowed tool or neighboring method:
- unavailable mechanism:
- surrogate mechanism:

### Challenge-to-Module Map

| Challenge | Failure mode | Design principle | Module | Evidence or ablation |
|---|---|---|---|---|

### Module Lens Table

| Module | Failure fixed | Ideal unavailable solution | Available proxy | Hidden assumption | Future research point |
|---|---|---|---|---|---|

### Citation Function Table

| Citation cluster | Narrative function | Assumption inherited | How this paper modifies it |
|---|---|---|---|

### Story Pattern Worth Reusing
- pattern name:
- compact formula:
- why it is reusable:

### Boundary-Pushing Idea List
- hidden assumption:
- what breaks if it fails:
- next mechanism worth exploring:
- linked claim IDs:

---

## Optional Storyboard Plan (Only if image generation is available)
### Panel 1
### Panel 2
### Panel 3
### Panel 4

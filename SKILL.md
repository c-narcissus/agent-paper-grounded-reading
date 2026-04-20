---
name: agent-paper-grounded-reading
description: Source-grounded paper reading skill for Codex and Claude Code-style local AI agent workflows. Generates a deep reading report, traceability artifacts, and an optional evidence reader.
metadata:
  version: "1.0.0"
  audience:
    - codex
    - claude-code-style-agents
  runtime:
    bins:
      - python
    python:
      - Markdown>=3.6
      - PyMuPDF>=1.24.0
    optional_bins:
      - pdflatex
      - synctex
---

# Agent Paper Grounded Reading

Use this skill in **local AI agent tools** when the user wants a **deep, paper-grounded reading report** for one computer-science paper or a small paper batch, starting from any of these inputs:

- a user-provided PDF
- a user-provided LaTeX source tree or `.tex` files
- only the paper title or citation-like paper name

The primary deliverable is a **detailed Markdown report**.
A secondary, optional deliverable is a **small sequence of connected cartoon images** that narrate the author’s idea, but only when an image-generation API or tool is available in the runtime and the user has not asked to suppress images.

## Usage Examples
- "Use `agent-paper-grounded-reading` to deeply read `paper.pdf` and create grounded report artifacts."
- "Use `agent-paper-grounded-reading` to read this paper from LaTeX source, validate every claim, and build the static evidence reader."

## Runtime Requirements

The bundled deep-reading scripts use Python 3.9+ standard library only; the static reader builder additionally requires `Markdown>=3.6` and `PyMuPDF>=1.24.0` from `requirements.txt`.
For LaTeX-to-PDF source highlighting, a TeX distribution that provides `pdflatex` and `synctex` is recommended.
For interactive web viewing, this complete package includes `scripts/build_reader_bundle.py`, `scripts/serve_bundle.py`, and `assets/reader_template/`; no separate reader skill is required.
Bundled scripts write only to user-specified output paths. This project is designed for Codex and Claude Code-style local agent workflows, not browser-only chat products. The static reader is an output artifact, not the primary runtime.

## Scope

This is a **standalone** skill.
Do **not** assume any upstream collection stage, bundle manifest, graph stage, canvas stage, spreadsheet stage, or downstream workflow.
Work directly from the paper materials currently available in the workspace, conversation, or fetchable from the web with the tools already available in the runtime.

## Core source-acquisition policy

Always try to assemble the **best available reading package** before writing the report.
The preferred evidence order is:

1. **LaTeX source from arXiv**, if available and relevant to the same paper version
2. **User-provided LaTeX source**
3. **User-provided PDF**
4. **Official paper PDF from arXiv, OpenReview, proceedings, or author page**
5. **Supplementary material, appendices, review threads, and rebuttals**

### A. When the user provides LaTeX

Use the provided LaTeX as the primary source.
Also use the compiled PDF if available, because figures, layout, and page-local argument flow are often easier to interpret in PDF form.

### B. When the user provides a PDF but not LaTeX

Treat the PDF as the initial source, but first check whether the same paper has an **arXiv source / LaTeX package** available.
If yes, prefer the arXiv LaTeX as the primary structural source and keep the PDF as a visual and pagination reference.
If no matching arXiv LaTeX is available, continue with the PDF and explicitly say that the analysis is PDF-primary.

### C. When the user provides only the paper title or a citation-like name

Search for the paper.
Try to obtain:

1. arXiv LaTeX/source package first
2. if no LaTeX is available, the best paper PDF
3. supplementary material if relevant
4. OpenReview thread if the venue is ICLR

When title matching is ambiguous, use authors, year, venue, abstract snippets, or method keywords to disambiguate.
Do not silently analyze the wrong paper.

### D. Matching discipline

When switching from a PDF or title to an arXiv source package, verify that the source corresponds to the same paper by checking as many of the following as possible:

- exact or near-exact title
- author list
- abstract
- venue / year / version notes
- core method names
- section structure

If there is a mismatch or uncertainty, say so explicitly and choose the most reliable source set.

## ICLR / OpenReview policy

If the target paper is an **ICLR paper**, try to retrieve the **same-year OpenReview submission page**.
Use it to collect, when available:

- reviewer comments
- meta-review or area-chair summary
- author rebuttal / response
- revision signals relevant to acceptance

Use these materials to enrich the deep reading report, especially for:

- what reviewers found convincing or weak
- which claims were challenged
- whether the rebuttal resolved those concerns
- how the review discussion changes confidence in the paper’s claims

If the OpenReview thread cannot be found, state that clearly and continue with the best grounded report possible.

## Output policy

Generate two coordinated output classes by default:

1. a **human-readable Markdown deep-reading report** that is pleasant to read on its own
2. a **machine-readable reader artifact set** that lets downstream tools connect report claims back to source evidence

When LaTeX source or another structured text source is available, generate these machine-readable artifacts next to the report:

- `latex_paragraphs.json`
- `traceability_manifest.json`
- `reader_artifacts.json`
- `storyboard_manifest.json` and/or `storyboard_prompts.md` when storyboard output is produced

These artifacts are part of the default deliverable for this skill because downstream grounded readers depend on them.
Use [templates/report_template.md](templates/report_template.md) for the report shape, [templates/traceability_manifest.template.json](templates/traceability_manifest.template.json) for the claim-evidence manifest shape, [templates/reader_artifacts.template.json](templates/reader_artifacts.template.json) for the portable reader file-set manifest, [templates/storyboard_manifest.template.json](templates/storyboard_manifest.template.json) for report-grounded storyboard metadata, [references/traceability-contract.md](references/traceability-contract.md) for field-level claim rules, and [references/reader-artifact-contract.md](references/reader-artifact-contract.md) for the page-reader artifact contract.
The paragraph index must preserve source file paths and line spans so downstream readers can use SyncTeX for line-accurate PDF highlighting rather than loose PDF text matching.

### Traceability-first requirement

Every user-facing report point must be grounded.
For each major report section, begin with `### Anchored Points` and list one or more claims in the exact form:

- `[C<section>.<index>] claim text`

Every claim ID that appears in the Markdown report must also appear in `traceability_manifest.json`.
Every claim must have at least one evidence row, and the evidence list must be exhaustive for that claim.
Every evidence row must point back to a source anchor:

- preferred: a LaTeX paragraph ID from `latex_paragraphs.json`
- fallback only when no LaTeX exists after explicit search: a PDF text-block anchor, clearly marked as fallback

Do not silently leave any claim ungrounded.
Do not omit supporting evidence when one report point depends on multiple original paragraphs, formulas, tables, figures, captions, or supplementary sections.
If a report point depends on several source locations, include one evidence row per materially necessary source location.
If a point actually contains multiple independent claims, split it into multiple anchored claims instead of hiding multiple arguments under one incomplete evidence row.
If a claim is only a plausible inference, still map it to the exact paragraph(s) that motivate the inference and mark the evidence relation accordingly.

### Validation step

Before finishing, run:

- `scripts/extract_latex_paragraphs.py` to build `latex_paragraphs.json`
- `scripts/validate_traceability.py` to verify that every anchored claim in the report is covered by the manifest and that every referenced paragraph ID exists

### Storyboard output

If an image-generation API or tool is available in the runtime, and the user has not opted out, generate a **small sequence of connected cartoon-style storyboard images** after the report.
Use the completed deep-reading report as the storyboard context, not only the paper abstract.
The storyboard should:

- narrate the author’s main idea step by step
- use recurring characters, objects, or visual metaphors across frames
- stay faithful to the report’s explanation
- simplify without distorting the method
- avoid adding scientific claims not supported by the paper
- save a `storyboard_prompts.md` or `storyboard_manifest.json` entry when file output is being produced, so the reader artifact set can reference the storyboard

When no image-generation capability is available, do not fail the task. Instead, include a short Markdown storyboard prompt set that could be used later.

## Language policy

Write the **skill instructions, internal prompts, and default report headings in English**.
Default to **English** for the report unless the user explicitly requests another language.

## Style policy

Stay close to the actual paper.
Do **not** drift into generic commentary.
Name the actual modules, formulas, assumptions, theorem objects, datasets, baselines, figures, captions, tables, empirical observations, and reviewer comments used in the paper.
Do not be overly brief.
Keep the report specific, evidence-backed, and somewhat concrete with paper-local details.
When inferring the author’s likely intentions or subjective judgments, distinguish clearly between:

- evidence-backed interpretation
- plausible inference
- speculation

## Grounded workflow

1. Assemble the best source package.
2. If LaTeX is available, extract paragraph anchors with `scripts/extract_latex_paragraphs.py`.
3. Draft the report using anchored claim IDs in the Markdown itself.
4. Fill `traceability_manifest.json` so each claim points to one or more paragraph IDs and PDF locator snippets.
5. Fill `reader_artifacts.json` to enumerate the report, traceability manifest, paragraph index, compiled PDFs, SyncTeX sidecars, and optional storyboard files.
6. Run `scripts/validate_traceability.py`.
7. If the runtime has image generation and the user has not opted out, generate the connected cartoon storyboard from the completed report context.
8. If the user also wants an interactive grounded reader, run the bundled `scripts/build_reader_bundle.py --artifact-manifest reader_artifacts.json`.
9. Only then finalize the report.

## Interactive reader build requirements

When this skill builds the bundled static reader, the artifact set must preserve:

- `latex_paragraphs.json` entries with `source_path`, `line_start`, and `line_end`
- compiled PDFs plus `.synctex.gz` or `.synctex` sidecars
- claim IDs in the report that exactly match the traceability manifest
- `reader_artifacts.json` with `schema_version: "paper-reader-artifacts/1.0"`

The bundled reader should then:

- use SyncTeX as the primary locator from LaTeX line spans to PDF coordinates
- keep the PDF pane and report pane independently scrollable
- give the PDF pane substantially more screen width than the report pane under normal desktop layouts
- scale the left PDF viewport so at least one complete PDF page is visible under normal desktop layouts
- allow users to zoom PDF content in or out inside the fixed PDF pane without resizing the surrounding layout
- keep report/evidence text compact enough that it does not crowd the PDF

## Mandatory report requirements

The report must explicitly cover the following whenever the available materials support it.

### 1. Paper identification and source package used

Report:

- title
- authors if available
- venue / year / status if available
- whether the reading was LaTeX-primary, PDF-primary, or mixed-source
- what sources were actually used
- whether arXiv LaTeX was searched for and whether it was found
- whether OpenReview materials were used

### 2. Title interpretation

Interpret the title term by term.
Explain what each keyword means, why the title is phrased that way, and how the title maps to the actual method, setting, and claims.

### 3. What problem the paper really solves

Explain:

- the direct paper-level problem
- the practical pain point
- the scientific question behind the method
- the upper multi-layer problem ladder

Prefer a continuous ladder such as:

- direction-native problem
- parent-field problem
- broader AI / ML problem

Also discuss upper problems suggested by:

- borrowed algorithm families
- bottlenecks introduced by the proposed method itself

### 4. Related work and cited-paper expansion

Do not only list cited papers.
For the key papers repeatedly discussed by the target paper, explain:

- what they solved
- what they still left open
- why the current paper needed to move beyond them
- how each one relates to the current paper
  - inherited
  - contrasted
  - generalized
  - specialized
  - hybridized
  - problem-shifted

### 5. Main idea and likely author reasoning path

Explain the core idea in paper-grounded terms.
Then reconstruct the likely reasoning path that led the authors from observed pain points and prior work to the final design.
When appropriate, discuss whether parts of the idea, theory choice, proof strategy, algorithm, or modules appear connected to the authors’ subjective judgments, research taste, heuristics, engineering preferences, or broader research style.

### 6. Symbols, concepts, and notation

Introduce important symbols, operators, assumptions, and problem-specific concepts before heavily relying on them.
Explain them in beginner-friendly language while remaining faithful to the paper.

### 7. Formula preservation and explanation

Do **not** omit key equations.
Preserve and explain the important:

- objective functions
- update rules
- constraints
- estimators
- bounds
- theorem statements

For each key formula, explain:

- what each symbol means
- why the formula is introduced
- what role it plays in the method
- which algorithm step or system behavior it corresponds to
- whether the formula itself appears limited, heuristic, fragile, or improvable

### 8. Theory, proof, and practice mapping

If the paper contains theory or proofs, explain:

- what is being proved
- why the authors chose to prove it
- what scientific or reviewer concern the proof addresses
- what practical meaning the theorem has

Then map theory to practice:

- theorem assumptions -> implementation assumptions
- proved objects -> implemented objects
- proof conclusions -> expected practical behavior

Judge whether theory and implementation are:

- exactly aligned
- approximately aligned
- only loosely connected

Also explain where theory stops being faithful to the actual implementation and whether that gap seems acceptable.

### 9. Algorithm or module walkthrough with concrete examples

Do not stop at equations.
Give a step-by-step explanation of the algorithm or module pipeline.
Whenever possible, include at least one concrete mini-example that instantiates:

- inputs
- states
- intermediate quantities
- outputs
- updates

### 10. Fine-grained critique of formulas, modules, and assumptions

Do not discuss only overall limitations.
Evaluate specific formulas, modules, and assumptions.
For central design elements, ask whether they are:

- brittle
- under-justified
- overly heuristic
- computationally expensive
- hard to optimize
- weakly identified
- mismatched to the claimed scientific goal

Then discuss:

- possible improvements
- alternative formulations
- likely trade-offs

### 11. Figures from both PDF and LaTeX

For **PDF papers**, explicitly interpret key figures instead of merely summarizing them.
For **LaTeX sources**, also reconstruct and explain important figures from figure environments, captions, labels, referenced text, and included image paths when possible.

For each important figure, explain:

- what the figure is trying to show
- how to read it
- what claim it supports
- whether the figure really supports that claim
- whether anything in the visual presentation is unclear, weak, or potentially misleading

### 12. Experimental design

Explain:

- datasets
- tasks
- baselines
- metrics
- ablations
- implementation details when available

Also connect the compared methods back to the related-work landscape in the introduction and related-work sections.

### 13. Table / chart / claim alignment audit

For each important table, plot, or result block, explain:

- what question it is answering
- what claim it is supposed to support
- whether it strongly supports, partially supports, or fails to support that claim
- whether there is any tension or inconsistency between results and claims
- plausible reasons for the mismatch, if any

### 14. Reviewer-lens audit

Include an explicit reviewer-style audit that comments on:

- novelty
- significance
- technical soundness
- methodology rigor
- reproducibility
- clarity of figures and tables
- results-claims alignment
- missing baselines or controls
- honesty about limitations

If ICLR OpenReview material is available, integrate reviewer concerns and author responses into this audit.

### 15. Innovation points and claim-by-claim support audit

List the paper’s main claimed contributions and judge, for each one, whether it is supported by:

- theory
- experiments
- qualitative evidence
- reviewer discussion
- only weak evidence

### 16. Weaknesses, limitations, and improvement room

Discuss:

- unresolved weaknesses
- failure modes
- scope limits
- strong assumptions
- hidden costs
- where the idea might break

### 17. Innovation type and boundary judgment

Judge whether the paper is mainly:

- incremental
- cross-pollinated
- conceptually reframing
- potentially boundary-pushing

Explain why.
Also discuss whether it actually crosses subfield or disciplinary boundaries, or mainly recombines known ideas inside the same lane.

### 18. Future directions

Propose future directions inspired by the paper, including:

- native next-step ideas
- cross-domain transfers
- stronger scientific-boundary directions
- alternative formulations or modules
- more decisive experiments

### 19. Simple vivid story summary

End with a simple, vivid, technically faithful story that helps a non-specialist remember the paper’s core idea.

### 20. Sources used

End with a short source list stating exactly which materials were used, such as:

- user PDF
- arXiv source package
- paper PDF
- supplementary PDF
- OpenReview thread
- author rebuttal
- screenshots

## Optional final step: storyboard generation

After the Markdown report is finished, check whether image generation is available.

- If yes, create a concise storyboard plan with 4–8 sequential panels and then generate the cartoon-style images.
- If no, provide only the storyboard plan and prompts in Markdown.

The storyboard should stay synchronized with the report’s explanation of:

- the original pain point
- the key intuition
- the core mechanism
- the training or inference flow
- the main empirical takeaway

## Failure handling

If some sources cannot be found, do not abort.
State clearly what was attempted, what was found, what was missing, and how that affects confidence.
Then continue with the best grounded report possible.

If LaTeX cannot be found after an explicit search, say so clearly and switch the traceability artifact to PDF-block fallback mode instead of pretending paragraph anchors exist.

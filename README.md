# Agent Paper Grounded Reading

[中文说明](./README.zh-CN.md)

![preview](./1.JPG)

`agent-paper-grounded-reading` is a **grounded + research-generative** paper-reading skill package for local AI agent tools such as **Codex, Trae, Claude Code / CC, and similar workflows**.

It is not a plain summarizer.
The package is built for users who want:

- a deep reading report
- claim-to-evidence traceability against PDF / LaTeX sources
- a mandatory static reader page for manual verification
- a structured research lens that helps mine **new paper ideas**

## Language Behavior

By default, the report follows the user's current request language.

- Chinese request -> Chinese report
- non-Chinese request -> English report
- explicit language request -> follow the explicit instruction

For Chinese reports, keep proper nouns and fixed technical identifiers in English.
This includes paper titles, method or module names, datasets, baselines, equation symbols, claim IDs, filenames, and JSON keys.

## What This Project Does

By default, the skill asks the agent to produce:

1. `report.md`
   A detailed, source-grounded deep reading report.
2. `traceability_manifest.json`
   Claim-to-evidence mappings for every anchored report claim.
3. `latex_paragraphs.json`
   Stable paragraph anchors with source paths and line spans when LaTeX or structured source is available.
4. `research_lens.json`
   A compact idea-mining artifact that extracts the paper's research equation, challenge-to-module logic, story pattern, and future directions.
5. `reader_artifacts.json`
   A portable manifest for building the static evidence reader.
6. `reader_bundle/` plus a local reader URL
   A built and launched static evidence reader for inspecting report claims against source evidence.
7. Optional storyboard files
   Prompt sets or images when image generation is available.

## Deep Reading Focus

The merged skill now combines two layers:

1. **Grounded auditability**
   Every important report claim should be traceable to LaTeX paragraphs or PDF fallback anchors.
2. **Research-generative analysis**
   The report should explain how the authors may have found the direction, what unavailable mechanism they replaced, how modules map to failure modes, why key citations matter, and what hidden assumptions can seed the next paper.

The default report therefore covers:

1. paper identification and source package used
2. one-sentence thesis and research equation
3. title interpretation
4. real problem and scientific problem ladder
5. likely author-side discovery path
6. story construction and challenge-to-module map
7. related work and reverse citation logic
8. formulas, theory, modules, figures, and experiments
9. claim-alignment and reviewer-style audit
10. story pattern worth learning
11. weaknesses, hidden assumptions, and boundary-pushing future ideas
12. vivid story summary and exact sources used

## Package Layout

- [SKILL.md](./SKILL.md)
  Main instructions for the local agent.
- [agents/openai.yaml](./agents/openai.yaml)
  UI-facing metadata.
- [references](./references)
  Contracts plus the research-generative methodology reference.
- [templates](./templates)
  Report, traceability, reader-artifact, storyboard, and research-lens templates.
- [scripts](./scripts)
  Paragraph extraction, PDF extraction, PDF snippet validation, reader bundle building, and bundle serving.
- [assets/reader_template](./assets/reader_template)
  The static evidence-reader UI.

## Static Reader

This repository includes a bundled reader page.
Every successful deep-reading run must build and launch this reader before finalizing.
After the report artifacts are prepared, the reader can:

- load the report beside the source PDF
- render the complete `report.md` first in the right-side pane, not a shortened claim summary
- highlight the whole relevant paragraph block from claim clicks
- scroll claim clicks from auxiliary cards/indexes back to the matching claim inside the full report body
- prefer SyncTeX over PDF text search when LaTeX exists
- use PDF fallback anchors and expand snippet hits to the containing paragraph block when only a PDF is available
- let users drag the divider between the evidence panel and PDF viewport
- render report formulas and evidence equations as readable math instead of raw LaTeX source
- convert report-body math delimiters and math-like inline code to MathML before Markdown rendering
- run `scripts/validate_reader_math.py` so raw LaTeX math does not silently remain in `report.html` or `evidence-map.json`
- surface research-equation and idea-mining summaries from `research_lens.json`

## Reusable Scripts

The packaged skill includes reusable tools extracted from PDF-only reading runs:

- `scripts/prepare_pdf_source.py`
  Extracts PDF text, page-level blocks, optional page previews, and an optional copied PDF into the output directory.
- `scripts/validate_pdf_snippets.py`
  Checks that every PDF fallback `locator_snippets` entry in `traceability_manifest.json` can be found by the same PyMuPDF search path used by the reader.
- `scripts/build_and_serve_reader.py`
  Builds `reader_bundle/`, validates math rendering, starts the local static server in the background, waits for HTTP 200, and writes `reader_url.txt`.
- `scripts/build_reader_bundle.py`
  Supports PDF-primary bundles without requiring a fake SyncTeX file when no `latex_paragraphs.json` is supplied.
  It renders `$...$`, `$$...$$`, `\(...\)`, `\[...\]`, and math-like inline code as MathML in the full report, claim text, and evidence text.
- `scripts/validate_reader_math.py`
  Fails the run if the built reader still contains raw LaTeX math delimiters, common raw LaTeX math commands, or fallback math spans.
- `templates/reader_artifacts_pdf.template.json`
  Provides a ready PDF-primary reader manifest shape without SyncTeX or `latex_paragraphs.json`.

## PDF-Only Fallback

For PDF-only papers, the skill now keeps the fallback path simple.

- fallback chain: `arXiv LaTeX -> PDF-only analysis and PDF anchors`
- first search for matching arXiv LaTeX
- if no matching LaTeX exists, continue directly with the PDF
- keep report-point localization explicit with PDF fallback anchors
- if the user explicitly forbids LaTeX/source use, do not search or read it
- run `prepare_pdf_source.py` before drafting and `validate_pdf_snippets.py` before building the reader
- for every source mode, build and launch the local static reader page so users can inspect paragraph-level highlights immediately

## Quick Use

If you are using the packaged skill zip in a local agent tool, place the skill package and the paper materials in the same workspace.

For LaTeX input:

```text
Please use agent-paper-grounded-reading to deeply read paper.tar.gz, preserve claim-to-evidence grounding, and extract new research directions.
```

For PDF input:

```text
Please use agent-paper-grounded-reading to deeply read paper.pdf, search for matching LaTeX if possible, produce the grounded report plus research_lens.json, build the static evidence reader, launch it locally, and return the local URL.
```

The reader is mandatory, so this is also valid:

```text
After finishing the report and artifacts, build and launch the static evidence reader bundle.
```

# Agent Paper Grounded Reading

[中文说明](./README.zh-CN.md)

`agent-paper-grounded-reading` is a source-grounded paper reading skill for local AI agent tools such as Codex, Claude Code-style workflows, and other agent runtimes that can read files, run scripts, and write reusable artifacts.

This project is not positioned as a browser-only prompt for chat products. Its primary runtime is a **local AI agent workflow**. The static web reader is an **output artifact**, not the runtime itself.

## What Makes It Different

Most paper tools stop at summary generation.
This project is built for **auditable deep reading**:

- it writes a human-readable deep reading report
- it assigns stable claim IDs such as `C5.2`
- it maps each claim back to one or many original evidence locations
- it validates that the claim-to-evidence mapping is complete
- it can build a static PDF/report evidence reader for manual inspection

In short: this is closer to a **paper analysis pipeline** than a paper summarizer.

## Key Features

- Human-readable deep reading report.
- Machine-readable traceability artifacts.
- LaTeX-first reading when arXiv or local LaTeX source is available.
- Stable claim IDs for report-to-source linking.
- Complete evidence coverage for claims supported by one or many source locations.
- LaTeX paragraph anchors with `source_path`, `line_start`, and `line_end`.
- SyncTeX-based PDF localization.
- PDF search fallback when SyncTeX or LaTeX is unavailable.
- Built-in static evidence reader.
- Multi-evidence highlighting in the reader.
- Main/supplementary PDF switching.
- Full-page PDF fit and in-pane zoom controls.
- Optional storyboard prompts and storyboard metadata.

## Best Fit

This repository is best used in:

- Codex
- Claude Code-style local agent workflows
- other local agent environments that can read local files and run Python scripts

It is **not primarily designed for ChatGPT Web** or similar browser-only chat interfaces.

ChatGPT Web can still consume the outputs after they are generated, for example:

- `report.md`
- `traceability_manifest.json`
- `latex_paragraphs.json`
- the generated static reader bundle

Practical workflow:

```text
local agent tool -> run the skill -> generate artifacts -> inspect/share outputs
```

## Repository Layout

```text
agent-paper-grounded-reading/
  SKILL.md
  README.md
  README.zh-CN.md
  requirements.txt
  agents/
  assets/
    reader_template/
  references/
  scripts/
  templates/
```

## Installation

### Codex

Copy the folder into your Codex skills directory:

```powershell
C:\Users\<you>\.codex\skills\agent-paper-grounded-reading
```

Then invoke it in a task with:

```text
Use $agent-paper-grounded-reading ...
```

### Claude Code-style workflows

Claude Code may not use the exact same skill-folder mechanism as Codex, but this repository still works well as an instruction-and-script bundle:

1. keep the repository locally
2. point the agent to `SKILL.md`
3. let the agent use the bundled scripts, templates, and references during execution

In practice, this repo works anywhere the agent can:

- read local files
- run Python scripts
- write output artifacts

## Requirements

Required:

```text
Python 3.9+
Markdown>=3.6
PyMuPDF>=1.24.0
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Recommended for best LaTeX-to-PDF evidence localization:

```text
pdflatex
synctex
```

Optional:

```text
image generation capability for storyboard output
```

The bundled scripts do not require credentials or environment variables.
They write only to user-specified output paths.

## Typical Workflow

### 1. Deep read a PDF

```text
Use $agent-paper-grounded-reading to deeply read ./paper.pdf.
Prefer arXiv LaTeX if available.
Produce a grounded report and traceability artifacts.
```

### 2. Read from local LaTeX source

```text
Use $agent-paper-grounded-reading to read ./paper_src/main.tex and ./paper.pdf.
Use LaTeX as the primary source and PDF as visual support.
Generate a grounded report and validate every claim against source evidence.
```

### 3. Run the full workflow

```text
Use $agent-paper-grounded-reading on this paper.
Create the deep reading report, complete claim-to-evidence artifacts, validate traceability, and build the interactive evidence reader.
```

## Generated Artifacts

The workflow can produce:

```text
report.md
traceability_manifest.json
latex_paragraphs.json
reader_artifacts.json
storyboard_manifest.json
storyboard_prompts.md
paper_reader_app/
```

### `report.md`

Human-readable deep reading report covering:

- paper identity and source package
- title interpretation
- real research problem
- scientific problem ladder
- related-work gap analysis
- likely author reasoning path
- symbols and notation
- formulas and equation-level explanations
- algorithm/module walkthrough
- figure and table interpretation
- experiment design and claim alignment
- reviewer-style audit
- contribution strength
- limitations and failure modes
- innovation type
- future directions
- vivid story summary

### `traceability_manifest.json`

Maps each claim in the report to one or more evidence rows.

### `latex_paragraphs.json`

Stores extracted paragraph anchors with:

- `paragraph_id`
- `tex_file`
- `source_path`
- `line_start`
- `line_end`
- `section_path`
- `text`

### `reader_artifacts.json`

Portable manifest used by the reader builder.

### `paper_reader_app/`

Static PDF/report evidence reader bundle.

## Evidence Completeness Rule

This project is stricter than most paper summarization tools.

If a report point depends on one source location, it gets one evidence row.
If it depends on multiple source locations, it must include all materially necessary evidence rows.

Evidence may come from:

- paragraphs
- formulas
- tables
- figures
- captions
- algorithms
- supplementary sections
- reviews or rebuttals when available

If a bullet contains multiple independent claims, split it into multiple claim IDs instead of hiding them under one incomplete evidence row.

## Static Reader

The built-in reader shows:

- paper PDF on the left
- report on the right
- clickable claims
- PDF highlights for one or many evidence spans
- paragraph IDs and line spans
- independent pane scrolling
- PDF zoom inside a fixed pane
- document switching for main and supplementary PDFs

Build it with:

```powershell
python scripts/build_reader_bundle.py --artifact-manifest reader_artifacts.json
```

Preview it with:

```powershell
python scripts/serve_bundle.py ./paper_reader_app --port 8765
```

## Scripts

### `scripts/extract_latex_paragraphs.py`

Extracts paragraph anchors from LaTeX files.

### `scripts/validate_traceability.py`

Checks:

- every report claim appears in the manifest
- every manifest claim appears in the report
- claim IDs are not duplicated
- every claim has evidence
- every paragraph ID exists

### `scripts/build_reader_bundle.py`

Builds the static evidence reader.

### `scripts/serve_bundle.py`

Serves the generated reader locally for preview.

## Project Identity

Recommended project name:

```text
agent-paper-grounded-reading
```

Recommended one-line description:

```text
Source-grounded paper reading skill for Codex and Claude Code-style local AI agent workflows.
```

Current repository version:

```text
1.0.0
```

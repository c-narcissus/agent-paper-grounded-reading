# Agent Paper Grounded Reading

[中文说明](./README.zh-CN.md)

![preview](./1.JPG)

A source-grounded paper reading skill for local AI agent workflows.

It produces not only a deep reading report, but also claim-to-evidence traceability artifacts and a static evidence reader for manual inspection.

## What It Does

This project helps an agent deeply read a paper and generate:

- a human-readable report
- stable claim IDs such as `C5.2`
- claim-to-evidence mappings
- LaTeX paragraph anchors
- a static interactive reader

It is designed for **auditable paper reading**, not just summary generation.

## Main Features

- LaTeX-first reading when source is available
- PDF fallback when LaTeX is unavailable
- claim-level traceability
- evidence completeness validation
- static reader for report + PDF inspection

## Best For

- Codex
- Claude Code-style local agent workflows
- other local agent tools that can read files, run Python, and write artifacts

## Quick Start

### 1. Put the files in your project directory

Place the following files in the same project directory:

- `agent-paper-grounded-reading-main.zip`
- your paper source archive, for example `paper.tar.gz`

Example:

```text
your-project/
  agent-paper-grounded-reading-main.zip
  paper.tar.gz
```

### 2. Ask Codex to use the skill

In Codex, simply say:

```text
Please use the skill in agent-paper-grounded-reading-main.zip to perform a deep reading of the paper contained in paper.tar.gz (LaTeX source).
```

Replace `paper.tar.gz` with your actual file name.

### 3. Check the outputs

Typical outputs include:

```text
report.md
traceability_manifest.json
latex_paragraphs.json
reader_artifacts.json
paper_reader_app/
```

## Outputs

### `report.md`
Human-readable deep reading report.

### `traceability_manifest.json`
Maps report claims to source evidence.

### `latex_paragraphs.json`
Stores extracted LaTeX paragraph anchors.

### `reader_artifacts.json`
Portable manifest for reader generation.

### `paper_reader_app/`
Static interactive evidence reader.

## Build the Reader

```bash
python scripts/build_reader_bundle.py --artifact-manifest reader_artifacts.json
python scripts/serve_bundle.py ./paper_reader_app --port 8765
```

## Requirements

- Python 3.9+
- Markdown>=3.6
- PyMuPDF>=1.24.0

Recommended:

- pdflatex
- synctex

## Version

`1.0.0`

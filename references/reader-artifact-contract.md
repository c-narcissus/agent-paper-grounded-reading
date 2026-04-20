# Reader Artifact Contract

The deep-reading workflow must produce two deliverable classes:

1. a human-readable deep-reading report
2. a machine-readable reader artifact set for interactive source/report alignment

## Required file set

The reader artifact set is coordinated by `reader_artifacts.json`.
Paths inside this file are relative to the manifest location unless absolute.

Required files:

- `report.md`
- `traceability_manifest.json`
- `latex_paragraphs.json`
- at least one compiled paper PDF
- the matching `.synctex.gz` or `.synctex` sidecar for each PDF whenever LaTeX is available

Recommended files:

- `report.pdf`
- `storyboard_manifest.json`
- `storyboard_prompts.md`
- storyboard image files, when an image-generation tool is available

Use [templates/storyboard_manifest.template.json](../templates/storyboard_manifest.template.json) when producing structured storyboard metadata.

## `reader_artifacts.json`

Use [templates/reader_artifacts.template.json](../templates/reader_artifacts.template.json) as the canonical shape.

Required top-level fields:

- `schema_version`: currently `paper-reader-artifacts/1.0`
- `report.markdown`
- `traceability_manifest`
- `latex_paragraphs`
- `documents[]`
- `documents[].doc`
- `documents[].pdf`
- `reader_output`

Recommended fields:

- `paper.title`
- `paper.source_mode`
- `report.pdf`
- `documents[].label`
- `documents[].synctex`
- `storyboard`

## Tool compatibility

The companion reader builder can consume either:

- explicit CLI arguments: `--report`, `--traceability`, `--paragraphs`, `--pdf`, `--output`
- one artifact manifest: `--artifact-manifest reader_artifacts.json`

The manifest route is preferred for portability because it keeps the human report, source PDFs, SyncTeX files, and evidence mappings in one parseable package.

## Invariants

- Every clickable report claim must have exactly one `claim_id`.
- Every `claim_id` in `report.md` must appear in `traceability_manifest.json`.
- Every evidence row must point to a valid `paragraph_id` in `latex_paragraphs.json`, unless the workflow explicitly falls back to a PDF-only anchor.
- If one claim depends on multiple original source locations, include all materially necessary locations as separate evidence rows.
- If one report bullet mixes multiple independent claims, split it into separate claim IDs before writing the manifest.
- When LaTeX is available, paragraph anchors must include `source_path`, `line_start`, and `line_end`.
- Reader builders should use SyncTeX first and only use PDF text search as a fallback.

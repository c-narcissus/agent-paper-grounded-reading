# Reader Artifact Contract

The deep-reading workflow must produce three deliverable classes:

1. a human-readable deep-reading report
2. a machine-readable reader artifact set for interactive source/report alignment
3. a machine-readable research lens artifact for idea generation and story-pattern extraction

## Required file set

The reader artifact set is coordinated by `reader_artifacts.json`.
Paths inside this file are relative to the manifest location unless absolute.

Required files:

- `report.md`
- `traceability_manifest.json`
- `research_lens.json`
- at least one compiled paper PDF
- the matching `.synctex.gz` or `.synctex` sidecar for each PDF whenever LaTeX is available

Required only when structured source text exists:

- `latex_paragraphs.json` or another paragraph index file referenced by `reader_artifacts.json`
- `latex_source_manifest.json` when `scripts/prepare_latex_source.py` staged, compiled, and indexed a LaTeX archive or source tree

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
- `research_lens`
- `documents[]`
- `documents[].doc`
- `documents[].pdf`
- `reader_output`

Required when a structured paragraph index exists:

- `latex_paragraphs` or `paragraph_index`

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
For LaTeX archives or source trees, prefer `scripts/prepare_latex_source.py --source <archive-or-dir> --output <run_dir> --compile` to create the staged `source/` tree, `latex_paragraphs.json`, `latex_source_manifest.json`, and a starter `reader_artifacts.json`.
After generating the portable bundle, workflows that want an immediately usable interactive reader should serve the `reader_output` directory with `scripts/serve_bundle.py`.
In PDF-primary mode, serving the bundle is recommended as the default finish step rather than an optional extra.
The preferred final wrapper is `scripts/build_and_serve_reader.py` because it builds the bundle, runs math validation, starts the local server, and writes the live URL.

## Reader UI contract

The right-side report pane must render the complete `report.md`/`report.html` content for every source mode.
Do not replace the report pane with a shortened claim list, research-lens card set, abstract, or generated digest.
Research-lens cards and claim-index cards may be included only as secondary navigation aids after the full report.
When a user clicks a claim from any auxiliary card or index, the reader should scroll to the matching anchored claim inside the full report body when that node exists.

## Math rendering contract

The built reader must display formulas and math symbols as rendered MathML, not raw LaTeX strings.
The builder must preprocess report Markdown math delimiters (`$...$`, `$$...$$`, `\(...\)`, `\[...\]`) and math-like inline code before Markdown conversion.
Short paper symbols written as inline code, including single-letter variables, bare subscripts/superscripts (`G_i`, `P_i^t`, `w_ij`), and Greek names (`alpha`, `phi_i`, `psi_i`), must render like equations rather than literal underscore text.
The builder must also render math in claim text and evidence text.
For LaTeX-source evidence paragraphs, the builder must sanitize visible evidence text by stripping presentational LaTeX commands and rendering equation environments as MathML, so the reader does not show raw `\begin{...}` blocks or underscore-style formulas.
`latex2mathml` is a required dependency for successful math rendering.
Do not treat a bundle containing `math-fallback` spans, raw math delimiters, common raw LaTeX math commands, math-like code spans, or bare `_i`/`^t` symbols as complete.
Run `scripts/validate_reader_math.py --bundle <reader_bundle>` after building and before serving or finalizing.

## Invariants

- Every clickable report claim must have exactly one `claim_id`.
- Every `claim_id` in `report.md` must appear in `traceability_manifest.json`.
- Every evidence row must point to a valid `paragraph_id` in `latex_paragraphs.json`, unless the workflow explicitly falls back to a PDF-only anchor.
- In PDF-primary mode, `pdf::...` anchors are valid even without a paragraph index file, as long as `locator_snippets` are strong enough for reliable PDF search.
- If one claim depends on multiple original source locations, include all materially necessary locations as separate evidence rows.
- If one report bullet mixes multiple independent claims, split it into separate claim IDs before writing the manifest.
- When LaTeX is available, paragraph anchors must include `source_path`, `line_start`, and `line_end`.
- Reader builders should use SyncTeX first and only use PDF text search as a fallback.
- Reader builders should preserve `line_start` / `line_end` for auditability when available, but should expand the visible PDF highlight to the containing paragraph block or text block when possible.
- In PDF-primary mode, a line or snippet hit must still expand to the containing paragraph or text block instead of staying as a thin line highlight.
- `research_lens.json` should only reference real report `claim_id` values and should compress the paper into reusable research patterns rather than repeating the report verbatim.
- The generated `report.html` and `evidence-map.json` must pass `validate_reader_math.py`.

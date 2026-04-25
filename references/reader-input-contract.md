# Input Contract

The reader skill consumes the grounded artifacts produced by the updated deep-reading skill.

Required inputs:

- `reader_artifacts.json`, preferred
- `report.md`
- `traceability_manifest.json`
- `latex_paragraphs.json`
- `research_lens.json`
- at least one compiled PDF
- the matching `.synctex.gz` or `.synctex` file for each compiled PDF

The builder can consume either explicit paths or the artifact manifest:

```powershell
python scripts/build_reader_bundle.py --artifact-manifest reader_artifacts.json
```

Use explicit arguments only when the artifact manifest is not available.

## `reader_artifacts.json`

Expected shape:

- `schema_version`, currently `paper-reader-artifacts/1.0`
- `report.markdown`
- `report.pdf`, optional
- `traceability_manifest`
- `latex_paragraphs`
- `research_lens`
- `documents[]`
- `documents[].doc`
- `documents[].pdf`
- `documents[].synctex`, recommended when LaTeX exists
- `reader_output`

## `traceability_manifest.json`

The reader expects the same schema described by the deep-reading skill:

- `paper.title`
- `claims[]`
- `claims[].claim_id`
- `claims[].section_id`
- `claims[].section_title`
- `claims[].claim_text`
- `claims[].evidence[]`
- `claims[].evidence[].doc`
- `claims[].evidence[].paragraph_id`
- `claims[].evidence[].quote`
- `claims[].evidence[].relation`
- `claims[].evidence[].locator_snippets`

`page_hint` is recommended because it makes PDF search more stable.
When SyncTeX is available, the reader uses `paragraph_id -> source_path + line span -> PDF coordinates` as the primary locator and only falls back to PDF text search when SyncTeX cannot resolve a paragraph.

## Claim granularity

Every clickable point in the UI corresponds to one `claim_id`.
If the report has finer-grained bullets, keep them separate in the manifest instead of merging them into a section-level blob.
If one clickable point depends on multiple original paragraphs, formulas, tables, figures, captions, or supplementary sections, keep all of them as separate `evidence[]` rows under the same claim.
The reader displays and highlights every evidence row; it should not collapse multiple source locations into one untraceable summary.

## Build output

The generated bundle is self-contained:

- the source PDFs are copied into the bundle
- page images are rendered into the bundle
- the report is converted to HTML inside the bundle
- the evidence map already includes the paragraph excerpt and the PDF highlight rectangles
- claims with multiple evidence rows remain multi-highlight claims in the UI
- the reader can surface research-equation and idea-generation summaries without replacing the original traceability surface
- the PDF pane supports in-pane zoom while preserving the surrounding layout size
- `reader-artifacts.json` is rewritten with bundle-local paths
- `source-reader-artifacts.json` is kept as provenance when the build used an upstream artifact manifest

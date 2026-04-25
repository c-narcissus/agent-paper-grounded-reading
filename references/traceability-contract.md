# Traceability Contract

The deep-reading skill now produces five coordinated artifacts:

- `report.md`: the human-readable report
- `latex_paragraphs.json` or another paragraph index file when structured source text exists
- `traceability_manifest.json`: claim-to-evidence mapping consumed by downstream readers
- `research_lens.json`: structured research-generative summary for idea mining
- `reader_artifacts.json`: portable file-set manifest for reader builders

## 1. Report-side claim format

Every claim that should be clickable in a reader must appear in the Markdown report as:

```md
- [C5.2] SemiDFL creates consensus in both data and model spaces.
```

Rules:

- `C<section>.<index>` is required
- claim IDs must be unique across the whole report
- every claim ID in the report must appear exactly once in `traceability_manifest.json`

## 2. Structured paragraph index

Expected top-level keys:

- `schema_version`, currently `paper-latex-paragraphs/1.0` when present
- `tex_root`
- `paragraphs`

Each paragraph entry must contain:

- `paragraph_id`
- `tex_file`
- `source_path`
- `section_path`
- `block_type`
- `line_start`
- `line_end`
- `text`
- `normalized_text`

Preferred `paragraph_id` format:

```text
main.tex::p0007
supplementary.tex::p0019
```

## 3. `traceability_manifest.json`

Expected top-level shape:

```json
{
  "schema_version": "paper-traceability/1.0",
  "paper": {
    "title": "Paper title",
    "source_mode": "latex-primary",
    "report_path": "paper_deep_reading.md"
  },
  "claims": [
    {
      "claim_id": "C1.1",
      "section_id": "1",
      "section_title": "Paper Identification and Source Package Used",
      "claim_text": "The title and author list come from the main paper title block.",
      "evidence": [
        {
          "evidence_id": "E-C1.1-a",
          "doc": "main",
          "paragraph_id": "main.tex::p0002",
          "quote": "Title block and author list in the paper front matter.",
          "relation": "direct",
          "page_hint": 1,
          "locator_snippets": [
            "SemiDFL: A Semi-Supervised Paradigm for Decentralized Federated Learning",
            "Xinyang Liu"
          ]
        }
      ]
    }
  ]
}
```

Required claim fields:

- `claim_id`
- `section_id`
- `section_title`
- `claim_text`
- `evidence`

Recommended claim fields:

- `interpretation_type`: `evidence-backed interpretation`, `plausible inference`, or `speculation`
- `research_role`: short label such as `direction reconstruction`, `module rationale`, `citation logic`, or `future idea`

Required evidence fields:

- `evidence_id`
- `doc`
- `paragraph_id`
- `quote`
- `relation`
- `locator_snippets`

Recommended evidence fields:

- `page_hint`
- `notes`

When LaTeX is available, `paragraph_id` should point to an entry that includes the original source file path and line span.
Those fields are consumed by SyncTeX-based readers to map report claims back to the compiled PDF with line-level precision.
When LaTeX is unavailable, `paragraph_id` may instead use a `pdf::...` fallback anchor.
In that case, the evidence row must still provide `locator_snippets` strong enough for PDF search, and the reader must expand the visual highlight to the containing paragraph or text block.

## 4. Coverage rules

- No claim may have an empty `evidence` list.
- If one report bullet makes two materially different statements, split it into two claims.
- If the support comes from multiple paragraphs, formulas, tables, figures, captions, or supplementary sections, include multiple evidence rows.
- The evidence list for each claim must be complete for the claim's actual meaning; do not include only the easiest matching paragraph when the report point depends on multiple source locations.
- If the claim is inferential rather than directly stated, set `relation` to `inference`.
- If no LaTeX exists after explicit search, replace `paragraph_id` with a clearly marked PDF fallback anchor and explain the fallback in `notes`.
- In PDF-primary mode, fallback anchors should still be paragraph-oriented in the reader: if the matched evidence is one line, the visible highlight should widen to that line's containing PDF paragraph or text block.
- If the claim reconstructs likely author reasoning, cite the exact motivating paragraphs and keep `interpretation_type` honest rather than presenting the reasoning as direct fact.

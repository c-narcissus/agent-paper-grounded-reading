# Research Lens Contract

`research_lens.json` is the structured artifact that turns a grounded paper reading into an idea-generation surface.
It must not replace the report or the traceability manifest.
Its job is to compress the paper into reusable research patterns while staying linked to real report claims.

## Required top-level fields

- `schema_version`, currently `paper-research-lens/1.0`
- `paper.title`
- `research_equation`
- `direction_reconstruction`
- `challenge_module_map`
- `module_lenses`
- `story_patterns`
- `boundary_directions`

`citation_logic` and `experiment_story_map` are strongly recommended whenever the paper has enough evidence.

## `research_equation`

This is the compact "why the paper exists" object.
It should capture:

- what old success or valuable paradigm already worked
- what hidden assumption broke
- what hard setting or realistic constraint mattered
- what neighboring tool almost transferred
- what unavailable mechanism `Y` was missing
- what surrogate mechanism `Z` the paper constructed
- one or more `claim_ids` that support the compression

## `direction_reconstruction`

This section reconstructs the likely author-side discovery path.
Use evidence-backed language such as:

- likely starting dissatisfaction
- almost-worked transfer
- blocking constraint
- replacement logic

Do not claim certainty about private author thoughts.
Link the reasoning back to real `claim_ids`.

## `challenge_module_map`

This table should map:

- challenge
- failure mode
- design principle
- module
- ablation or evidence

The goal is to show how the paper turns problems into defendable modules rather than into arbitrary engineering.

## `module_lenses`

For each central module, capture:

- the failure it fixes
- the ideal but unavailable solution
- the available proxy
- the hidden assumption
- the next research direction if that assumption breaks

This is the main bridge from understanding to idea generation.

## `story_patterns`

Extract the paper-making pattern worth reusing.
Examples:

- replacement story
- three-module story
- closed-loop contribution
- two-axis empty-cell positioning
- hidden-assumption break

The `formula` may be prose or compact math-like notation, but it should stay readable.

## `boundary_directions`

These are the strongest next-step ideas.
Each entry should explain:

- the hidden assumption
- what breaks if it fails
- what stronger mechanism or setting is worth exploring next
- which report `claim_ids` motivate the idea

## Invariants

- Every `claim_ids` entry must refer to a real report claim ID.
- `research_lens.json` should help a reader invent follow-up work, not merely repeat section headings.
- The file should stay concise enough to scan quickly.
- It must never contradict `traceability_manifest.json` or the report.

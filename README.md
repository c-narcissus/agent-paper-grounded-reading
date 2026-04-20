# Agent Paper Grounded Reading

[中文说明](./README.zh-CN.md)

![preview](./1.JPG)

`agent-paper-grounded-reading` is a deep-reading skill for local AI agent workflows.

It is not designed as a plain paper summarizer. The goal is to produce grounded, auditable analysis that can be checked against original PDF / LaTeX evidence, including visual inspection in a static reader page.

## Deep Reading Outline and Focus

By default, the reading report covers these areas, with emphasis on how each part supports or questions the paper's actual claims:

1. **Paper identity and source package**
   Clarifies title, authors, version, and which materials were actually used in the reading.
2. **Title interpretation and real research problem**
   Explains what the title terms mean and what problem the paper is really trying to solve.
3. **Scientific problem ladder**
   Expands from the direct task to higher-level research and broader AI / ML questions.
4. **Related-work gap analysis**
   Explains what the paper inherits, what it moves beyond, and what gap it is really filling.
5. **Likely author reasoning path**
   Reconstructs why the method was probably designed this way instead of only restating module names.
6. **Symbols, concepts, and notation**
   Introduces the key objects and notation before relying on formulas and algorithms.
7. **Formulas and equation-level explanations**
   Covers objectives, update rules, thresholds, generative targets, and what each formula does in the method.
8. **Algorithm / module walkthrough**
   Explains inputs, states, intermediate quantities, and outputs step by step.
9. **Figure and table interpretation**
   Explains what each figure or table is trying to support and whether it really supports that claim.
10. **Experiment design and claim alignment**
    Covers datasets, tasks, baselines, metrics, ablations, and whether the empirical evidence matches the paper's claims.
11. **Reviewer-style audit**
    Judges novelty, technical reliability, reproducibility, and result credibility.
12. **Contribution strength**
    Audits how strongly each claimed contribution is supported instead of treating all contributions equally.
13. **Limitations and failure modes**
    Points out where the method may break, which assumptions are strong, and which modules are costly or fragile.
14. **Innovation type**
    Judges whether the paper is incremental, recombinational, cross-directional, or more boundary-pushing.
15. **Future directions**
    Suggests stronger next steps and more decisive follow-up evaluations.
16. **Vivid story summary**
    Ends with a simple but faithful way to remember the paper's core idea.

## Quick Use

Put these in the same directory:

- `agent-paper-grounded-reading-main.zip`
- the paper file, such as `paper.tar.gz`, `paper.pdf`, or a local LaTeX source tree

If the input is a LaTeX package, in Codex you can say:

```text
Please use the skill in agent-paper-grounded-reading-main.zip to deeply read the paper in paper.tar.gz (latex).
```

If the input is a PDF, you can say:

```text
Please use the skill in agent-paper-grounded-reading-main.zip to deeply read paper.pdf.
```

Replace `paper.tar.gz` or `paper.pdf` with the real filename.

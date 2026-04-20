# Agent Paper Grounded Reading

[中文说明](./README.zh-CN.md)
![preview](./1.JPG)

A source-grounded paper reading skill for local AI agent workflows such as Codex and Claude Code-style environments.

## What It Does

This project helps an agent deeply read a paper and produce:

- a human-readable report
- claim-to-evidence traceability artifacts
- LaTeX paragraph anchors
- a static interactive evidence reader

It is designed for **auditable paper reading**, not just summary generation.

## Main Features

- Deep reading report with stable claim IDs such as `C5.2`
- Claim-to-evidence mapping
- LaTeX-first reading when source is available
- PDF fallback when LaTeX is unavailable
- Static reader for report + PDF inspection
- Traceability validation scripts

## Best For

- Codex
- Claude Code-style local agent workflows
- other local agent tools that can read files, run Python, and write artifacts

## Quick Start

### 1. Put the files in your project directory

Place the following files in your project directory:

- `agent-paper-grounded-reading-main.zip`
- your paper source archive, such as `xxx.tar.gz` (LaTeX source)

Example:

```text
your-project/
  agent-paper-grounded-reading-main.zip
  paper.tar.gz




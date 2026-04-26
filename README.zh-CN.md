# Agent Paper Grounded Reading

[English README](./README.md)

![preview](./1.JPG)

`agent-paper-grounded-reading` 是面向 **Codex、Trae、Claude Code / CC 以及类似本地 AI Agent 工作流** 的论文精读 skill 包。

它不是普通摘要器。这个项目的目标是同时做到：

- **grounded 可追溯**：报告里的关键判断都能回查到 PDF / LaTeX 原始证据。
- **research-generative 可产出新 idea**：不只解释论文做了什么，还解释作者可能怎么想到这个方向、为什么这样组织 story、哪些隐藏假设可以继续推进成下一篇论文。

## 默认产物

默认要求 agent 产出以下文件：

- `report.md`：面向人阅读的精读主报告。
- `traceability_manifest.json`：报告 claim 到原始证据的映射。
- `latex_paragraphs.json`：当 LaTeX 或结构化源码可用时，保存源文件路径与行号的段落锚点。
- `research_lens.json`：研究生成视角的结构化产物，提炼 research equation、challenge-to-module 结构、story pattern 和后续 idea。
- `reader_artifacts.json`：静态 reader 的输入清单。
- `reader_bundle/` 和本地 reader URL：已构建并启动的静态证据阅读页。
- 可选 storyboard 产物：当运行环境支持图片生成时，额外输出分镜 prompt 或图片。

## 分析方法

这个 skill 合并了 grounded 精读和 research-generative 方法学，要求报告覆盖：

- 论文身份与实际使用的 source package。
- 一句话 thesis 与 research equation。
- 标题拆解、真实问题和 scientific problem ladder。
- 作者可能如何发现方向、如何搭建 story。
- related work 与关键 citation 的叙事角色。
- 公式、理论、模块、图表和实验的逐层解释。
- claims 与 evidence 是否真正对齐。
- 最值得复用的 story-making pattern。
- 隐藏假设、薄弱点与边界推进方向。
- 最后用一个简单但忠实的故事收束。

## 目录结构

- [SKILL.md](./SKILL.md)：主 skill 说明。
- [agents/openai.yaml](./agents/openai.yaml)：面向工具 UI 的展示元数据。
- [references](./references)：traceability、reader 和 research-generative 方法学参考。
- [templates](./templates)：报告、traceability、reader artifact、storyboard 和 `research_lens.json` 模板。
- [scripts](./scripts)：段落抽取、PDF 抽取、PDF snippet 校验、reader bundle 构建和本地预览脚本。
- [assets/reader_template](./assets/reader_template)：静态证据阅读页模板。

## 页面能力

主 skill 自带静态 reader 页面。每次成功的精读任务都必须在结束前构建并启动这个页面。构建完成后，页面可以：

- 左侧查看 PDF，右侧查看报告。
- 右侧优先完整渲染 `report.md`，不能用简化 claim 列表或 research cards 替代完整报告。
- 点击 claim 高亮对应证据。
- 从辅助 cards/index 点击 claim 时，会回到完整报告正文里的对应 claim。
- 在有 LaTeX / SyncTeX 时优先做精确定位。
- 在 PDF-only 模式下使用 `locator_snippets` 定位并扩展到 PDF 段落块。
- 将报告正文里的 `$...$`、`$$...$$`、`\(...\)`、`\[...\]` 和数学 inline code 转成 MathML，而不是显示 raw LaTeX。
- 通过 `scripts/validate_reader_math.py` 检查 `report.html` 和 `evidence-map.json`，避免 raw LaTeX 静默留在网页里。
- 读取 `research_lens.json`，以页面卡片形式展示 research equation、story logic 和 future ideas。

## 可复用脚本

这次 PDF-only 精读流程中可复用的工具已经沉淀到 `scripts/`：

- `scripts/prepare_pdf_source.py`：抽取 PDF 文本、页级 text blocks、可选页面预览图，并可把 PDF 复制到输出目录。
- `scripts/validate_pdf_snippets.py`：校验 `traceability_manifest.json` 里的 PDF fallback `locator_snippets` 是否能被 reader 使用的 PyMuPDF 搜索路径找到。
- `scripts/build_and_serve_reader.py`：构建 `reader_bundle/`，校验数学渲染，后台启动本地静态服务，等待 HTTP 200，并写出 `reader_url.txt`。
- `scripts/build_reader_bundle.py`：在 PDF-primary 且没有 `latex_paragraphs.json` 时，不再需要假的 SyncTeX 文件；同时把报告、claim 和 evidence 里的 LaTeX 数学转成 MathML。
- `scripts/validate_reader_math.py`：如果构建后的网页仍包含 raw LaTeX 数学定界符、常见 raw LaTeX 数学命令或 fallback math spans，就让运行失败。
- `templates/reader_artifacts_pdf.template.json`：提供不含 SyncTeX 和 `latex_paragraphs.json` 的 PDF-primary reader manifest 模板。

## PDF-Only 流程

如果输入是 PDF，默认先尝试匹配 arXiv LaTeX；如果找不到，就继续使用 PDF-primary 和 PDF fallback anchors。

如果用户明确禁止读取 LaTeX 或 source，则不要搜索、解包或读取 LaTeX/source；直接使用 PDF-primary 流程，并在报告中说明这个来源约束。

PDF-primary 时应先运行：

```text
python scripts/prepare_pdf_source.py --pdf paper.pdf --output <run_dir> --doc-key paper --copy-pdf
```

构建 reader 前应运行：

```text
python scripts/validate_pdf_snippets.py --traceability traceability_manifest.json --pdf paper=paper.pdf
```

最后必须构建并启动静态页面：

```text
python scripts/build_and_serve_reader.py --artifact-manifest reader_artifacts.json --url-file reader_url.txt
```

## 快速使用

LaTeX 输入示例：

```text
请使用 agent-paper-grounded-reading 对 paper.tar.gz 做 grounded 精读，同时提取研究视角下的新 idea。
```

PDF 输入示例：

```text
请使用 agent-paper-grounded-reading 对 paper.pdf 做精读；如果能找到匹配的 arXiv LaTeX，就切换到 LaTeX-primary；否则走 PDF-primary。输出 report.md、traceability_manifest.json、research_lens.json，构建并启动静态 evidence reader，然后返回本地 URL。
```

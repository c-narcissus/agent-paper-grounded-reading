# Agent Paper Grounded Reading

[English README](./README.md)
![preview](./1.JPG)
`agent-paper-grounded-reading` 是一个面向本地 AI agent 工具的、基于原文证据的论文精读 skill，适用于 Codex、Claude Code 风格工作流，以及其他可以读取文件、执行脚本、生成可复用工件的本地 agent 环境。

这个项目的定位不是“给网页聊天产品用的一段 prompt”，而是“给本地 agent 用的一整套论文精读工作流”。  
静态网页 reader 是工作流的输出产物，不是项目本身的运行环境。

## 它和一般论文工具的区别

大多数论文工具停留在“生成摘要”这一步。  
这个项目面向的是**可追责的深度精读**：

- 生成人可读的深度精读报告
- 给每个关键观点分配稳定 claim ID，例如 `C5.2`
- 把每个 claim 映射回一处或多处原始 evidence
- 校验 claim 到 evidence 的映射是否完整
- 在需要时构建一个静态 PDF / 报告证据阅读器，方便人工检查

一句话说，它更像是一个**论文分析流水线**，而不是普通的论文总结器。

## 核心特性

- 生成人类可读的深度精读报告
- 生成工具可读的结构化 traceability artifacts
- 在 arXiv 或本地 LaTeX 可用时优先使用 LaTeX
- 使用稳定 claim ID 进行报告与原文映射
- 支持一个 claim 对应一处或多处 evidence
- LaTeX 段落锚点保留 `source_path`、`line_start`、`line_end`
- 支持基于 SyncTeX 的 PDF 定位
- 当 SyncTeX / LaTeX 不可用时支持 PDF 搜索降级
- 内置静态证据阅读器
- 支持多 evidence 高亮
- 支持主文 / supplementary PDF 切换
- 支持整页适配和 PDF 区域内缩放
- 支持 storyboard prompts 和 storyboard metadata

## 最适合的使用场景

这个仓库最适合运行在：

- Codex
- Claude Code 风格的本地 agent 工作流
- 其他可以读取本地文件、运行 Python 脚本的本地 agent 环境

它**不是主要为 ChatGPT 网页版设计的**。

不过，ChatGPT Web 仍然可以使用这个项目生成后的产物，例如：

- `report.md`
- `traceability_manifest.json`
- `latex_paragraphs.json`
- 生成好的静态 reader bundle

推荐工作流：

```text
本地 agent 工具 -> 运行 skill -> 生成 artifacts -> 再人工检查 / 分享结果
```

## 仓库结构

```text
agent-paper-grounded-reading/
  1.JPG
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

## 安装方式

### Codex

把目录放到 Codex 的 skills 目录下：

```powershell
C:\Users\<you>\.codex\skills\agent-paper-grounded-reading
```

然后在任务中这样调用：

```text
Use $agent-paper-grounded-reading ...
```

### Claude Code 风格工作流

Claude Code 不一定和 Codex 使用完全相同的 skill 目录机制，但这个仓库仍然可以作为“说明 + 脚本 + 模板 + reference”的完整包使用：

1. 把仓库保存在本地
2. 让 agent 读取 `SKILL.md`
3. 允许 agent 在执行过程中使用其中的脚本、模板和 references

本质上，只要 agent 具备以下能力，这个仓库就能工作：

- 读取本地文件
- 运行 Python 脚本
- 写出结果文件

## 依赖要求

必需：

```text
Python 3.9+
Markdown>=3.6
PyMuPDF>=1.24.0
```

安装依赖：

```powershell
pip install -r requirements.txt
```

为了获得更好的 LaTeX 到 PDF 证据定位效果，推荐安装：

```text
pdflatex
synctex
```

可选：

```text
图像生成能力，用于 storyboard 输出
```

项目内置脚本不需要密钥，也不依赖环境变量。  
脚本只会写入用户指定的输出目录。

## 典型使用方式

### 1. 精读一篇 PDF 论文

```text
Use $agent-paper-grounded-reading to deeply read ./paper.pdf.
Prefer arXiv LaTeX if available.
Produce a grounded report and traceability artifacts.
```

### 2. 从本地 LaTeX 源码精读

```text
Use $agent-paper-grounded-reading to read ./paper_src/main.tex and ./paper.pdf.
Use LaTeX as the primary source and PDF as visual support.
Generate a grounded report and validate every claim against source evidence.
```

### 3. 跑完整流程

```text
Use $agent-paper-grounded-reading on this paper.
Create the deep reading report, complete claim-to-evidence artifacts, validate traceability, and build the interactive evidence reader.
```

## 生成产物

整个流程可以生成如下文件：

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

给人阅读的深度精读报告，通常覆盖：

- 论文身份与来源材料
- 标题解释
- 真正的问题定义
- 科学问题阶梯
- 相关工作缺口分析
- 作者可能的推理路径
- 符号与记号说明
- 关键公式与逐式解释
- 算法 / 模块 walkthrough
- 图表解释
- 实验设计与结论对齐
- reviewer 视角审计
- 贡献强度分析
- 局限与失败模式
- 创新类型判断
- 未来方向
- 生动故事总结

### `traceability_manifest.json`

把报告中的每个 claim 映射到一条或多条 evidence。

### `latex_paragraphs.json`

保存抽取出的 LaTeX 段落锚点，包括：

- `paragraph_id`
- `tex_file`
- `source_path`
- `line_start`
- `line_end`
- `section_path`
- `text`

### `reader_artifacts.json`

供 reader builder 使用的可移植 manifest。

### `paper_reader_app/`

静态 PDF / 报告证据阅读器 bundle。

## 证据完整性规则

这个项目比一般论文总结工具更严格。

如果一个报告点只依赖一处原文依据，就映射一条 evidence。  
如果一个报告点依赖多处原文依据，就必须把所有“实质上必要”的 evidence 全部列出来。

evidence 可能来自：

- 段落
- 公式
- 表格
- 图片
- caption
- 算法描述
- supplementary 部分
- review / rebuttal（如果存在）

如果一个 bullet 实际上混合了多个独立判断，就应该拆成多个 claim ID，而不是塞进一个证据不完整的 claim。

## 静态阅读器

内置 reader 支持：

- 左侧显示论文 PDF
- 右侧显示精读报告
- 点击 claim 跳转并高亮 evidence
- 一个 claim 支持一处或多处高亮
- 显示段落 ID 和行号范围
- 左右独立滚动
- 固定 PDF 区域内缩放
- 主文 / supplementary 文档切换

构建方式：

```powershell
python scripts/build_reader_bundle.py --artifact-manifest reader_artifacts.json
```

本地预览：

```powershell
python scripts/serve_bundle.py ./paper_reader_app --port 8765
```

## 脚本说明

### `scripts/extract_latex_paragraphs.py`

从 LaTeX 文件中抽取段落锚点。

### `scripts/validate_traceability.py`

检查：

- 报告中的 claim 是否都出现在 manifest 中
- manifest 中的 claim 是否都在报告中出现
- claim ID 是否重复
- 每个 claim 是否至少有一条 evidence
- 每个 paragraph ID 是否真实存在

### `scripts/build_reader_bundle.py`

构建静态证据阅读器。

### `scripts/serve_bundle.py`

本地启动生成好的 reader 进行预览。

## 项目定位

推荐项目名：

```text
agent-paper-grounded-reading
```

推荐一句话说明：

```text
Source-grounded paper reading skill for Codex and Claude Code-style local AI agent workflows.
```

当前仓库版本：

```text
1.0.0
```

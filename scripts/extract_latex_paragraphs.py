import argparse
import json
import re
from pathlib import Path


SECTION_PATTERN = re.compile(
    r"\\(?P<level>section|subsection|subsubsection)\*?(?:\[[^\]]*\])?{(?P<title>[^{}]+)}"
)
COMMENT_PATTERN = re.compile(r"(?<!\\)%.*$")


def strip_comments(line: str) -> str:
    return COMMENT_PATTERN.sub("", line).rstrip()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def classify_block(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith("\\caption"):
        return "caption"
    if stripped.startswith("\\item"):
        return "list-item"
    if stripped.startswith("\\"):
        return "command-block"
    return "paragraph"


def should_keep(text: str) -> bool:
    compact = normalize_text(text)
    if len(compact) < 20:
        return False
    return bool(re.search(r"[A-Za-z0-9]", compact))


def flush_buffer(entries, tex_file: Path, root: Path, section_path, counter, buffer, line_start, line_end):
    text = normalize_text(" ".join(buffer))
    buffer.clear()
    if not should_keep(text):
        return counter, None, None

    counter += 1
    entries.append(
        {
            "paragraph_id": f"{tex_file.name}::p{counter:04d}",
            "tex_file": str(tex_file.relative_to(root)).replace("\\", "/"),
            "source_path": str(tex_file.resolve()),
            "section_path": list(section_path),
            "block_type": classify_block(text),
            "line_start": line_start,
            "line_end": line_end,
            "text": text,
            "normalized_text": text.lower(),
        }
    )
    return counter, None, None


def extract_from_file(tex_file: Path, root: Path):
    entries = []
    section_stack = []
    buffer = []
    counter = 0
    in_abstract = False
    line_start = None
    line_end = None

    for line_number, raw_line in enumerate(tex_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = strip_comments(raw_line)
        stripped = line.strip()

        if stripped == r"\begin{abstract}":
            counter, line_start, line_end = flush_buffer(
                entries, tex_file, root, section_stack, counter, buffer, line_start, line_end
            )
            in_abstract = True
            section_stack = ["Abstract"]
            continue

        if stripped == r"\end{abstract}":
            counter, line_start, line_end = flush_buffer(
                entries, tex_file, root, section_stack, counter, buffer, line_start, line_end
            )
            in_abstract = False
            section_stack = []
            continue

        match = SECTION_PATTERN.match(stripped)
        if match:
            counter, line_start, line_end = flush_buffer(
                entries, tex_file, root, section_stack, counter, buffer, line_start, line_end
            )
            level = match.group("level")
            title = normalize_text(match.group("title"))
            depth = {"section": 1, "subsection": 2, "subsubsection": 3}[level]
            section_stack = section_stack[: depth - 1]
            section_stack.append(title)
            continue

        if not stripped:
            counter, line_start, line_end = flush_buffer(
                entries, tex_file, root, section_stack, counter, buffer, line_start, line_end
            )
            continue

        if in_abstract and not section_stack:
            section_stack = ["Abstract"]

        if line_start is None:
            line_start = line_number
        line_end = line_number
        buffer.append(stripped)

    flush_buffer(entries, tex_file, root, section_stack, counter, buffer, line_start, line_end)
    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tex-root", required=True)
    parser.add_argument("--tex", action="append", required=True, help="Relative or absolute .tex file path")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.tex_root).resolve()
    paragraphs = []
    for tex_arg in args.tex:
        tex_path = Path(tex_arg)
        if not tex_path.is_absolute():
            tex_path = root / tex_path
        tex_path = tex_path.resolve()
        paragraphs.extend(extract_from_file(tex_path, root))

    output = {
        "schema_version": "paper-latex-paragraphs/1.0",
        "tex_root": str(root),
        "paragraphs": paragraphs,
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXTRACT_PARAGRAPHS = SCRIPT_DIR / "extract_latex_paragraphs.py"


def is_within_directory(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def safe_extract_tar(archive: Path, target: Path) -> None:
    with tarfile.open(archive, "r:*") as handle:
        for member in handle.getmembers():
            member_path = target / member.name
            if not is_within_directory(target, member_path):
                raise RuntimeError(f"Unsafe archive path: {member.name}")
        try:
            handle.extractall(target, filter="data")
        except TypeError:
            handle.extractall(target)


def safe_extract_zip(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            member_path = target / member.filename
            if not is_within_directory(target, member_path):
                raise RuntimeError(f"Unsafe archive path: {member.filename}")
        handle.extractall(target)


def copy_or_extract_source(source: Path, source_dir: Path) -> str:
    source = source.resolve()
    source_dir.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        for item in source.iterdir():
            destination = source_dir / item.name
            if item.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destination)
        return "directory"

    name = source.name.lower()
    if name.endswith((".tar.gz", ".tgz", ".tar", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
        safe_extract_tar(source, source_dir)
        return "tar"
    if name.endswith(".zip"):
        safe_extract_zip(source, source_dir)
        return "zip"
    if source.suffix.lower() == ".tex":
        shutil.copy2(source, source_dir / source.name)
        return "single-tex"
    raise RuntimeError(f"Unsupported LaTeX source input: {source}")


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def tex_score(path: Path, text: str) -> int:
    lower = path.name.lower()
    score = 0
    if "\\documentclass" in text:
        score += 50
    if "\\begin{document}" in text:
        score += 50
    if lower == "main.tex":
        score += 40
    if lower in {"paper.tex", "ms.tex", "article.tex"}:
        score += 25
    if "supp" in lower or "appendix" in lower:
        score += 15
    if "\\title" in text:
        score += 10
    return score


def discover_tex_files(source_dir: Path, explicit_tex: list[str]) -> list[Path]:
    if explicit_tex:
        result = []
        for value in explicit_tex:
            path = Path(value)
            if not path.is_absolute():
                path = source_dir / path
            result.append(path.resolve())
        return result

    candidates = []
    for path in source_dir.rglob("*.tex"):
        text = read_text(path)
        score = tex_score(path, text)
        if score >= 80:
            candidates.append((score, path))

    if not candidates:
        candidates = [(tex_score(path, read_text(path)), path) for path in source_dir.rglob("*.tex")]

    candidates.sort(key=lambda item: (-item[0], str(item[1]).lower()))
    selected = []
    for _, path in candidates:
        if path not in selected:
            selected.append(path)
    return selected


def relative_to_source(path: Path, source_dir: Path) -> str:
    return str(path.resolve().relative_to(source_dir.resolve())).replace("\\", "/")


def relative_to_output(path: Path, output_dir: Path) -> str:
    return str(path.resolve().relative_to(output_dir.resolve())).replace("\\", "/")


def run_compile(tex_path: Path, compiler: str, rounds: int) -> dict:
    logs = []
    success = True
    for round_index in range(1, rounds + 1):
        log_path = tex_path.with_suffix(f".compile{round_index}.log")
        command = [
            compiler,
            "-synctex=1",
            "-interaction=nonstopmode",
            tex_path.name,
        ]
        completed = subprocess.run(
            command,
            cwd=str(tex_path.parent),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        log_path.write_text(completed.stdout or "", encoding="utf-8", errors="replace")
        logs.append(str(log_path))
        if completed.returncode != 0:
            success = False
            break

    pdf_path = tex_path.with_suffix(".pdf")
    synctex_gz = tex_path.with_suffix(".synctex.gz")
    synctex = tex_path.with_suffix(".synctex")
    return {
        "tex": str(tex_path),
        "success": success,
        "pdf": str(pdf_path) if pdf_path.exists() else "",
        "synctex": str(synctex_gz if synctex_gz.exists() else synctex) if (synctex_gz.exists() or synctex.exists()) else "",
        "logs": logs,
    }


def run_paragraph_extraction(source_dir: Path, tex_files: list[Path], output_path: Path) -> None:
    command = [
        sys.executable,
        str(EXTRACT_PARAGRAPHS),
        "--tex-root",
        str(source_dir),
        "--output",
        str(output_path),
    ]
    for tex_file in tex_files:
        command.extend(["--tex", relative_to_source(tex_file, source_dir)])
    subprocess.run(command, check=True)


def write_reader_artifacts(output_dir: Path, title: str, documents: list[dict], source_mode: str) -> Path:
    payload = {
        "schema_version": "paper-reader-artifacts/1.0",
        "paper": {
            "title": title or "<paper title>",
            "source_mode": source_mode,
        },
        "report": {
            "markdown": "report.md",
        },
        "traceability_manifest": "traceability_manifest.json",
        "latex_paragraphs": "latex_paragraphs.json",
        "research_lens": "research_lens.json",
        "documents": documents,
        "storyboard": {
            "manifest": "storyboard_manifest.json",
            "prompts": "storyboard_prompts.md",
            "images": [],
        },
        "reader_output": "reader_bundle",
    }
    path = output_dir / "reader_artifacts.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def infer_title(tex_files: list[Path]) -> str:
    for tex_file in tex_files:
        text = read_text(tex_file)
        marker = "\\title{"
        start = text.find(marker)
        if start == -1:
            continue
        index = start + len(marker)
        depth = 1
        chars = []
        while index < len(text) and depth:
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
            chars.append(char)
            index += 1
        title = " ".join("".join(chars).split())
        if title:
            return title
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a LaTeX source package for grounded paper reading."
    )
    parser.add_argument("--source", required=True, help="LaTeX directory, .tex file, .zip, or tar archive.")
    parser.add_argument("--output", required=True, help="Run output directory.")
    parser.add_argument("--tex", action="append", help="Explicit .tex entrypoint relative to the extracted source.")
    parser.add_argument("--compile", action="store_true", help="Compile selected TeX files with SyncTeX.")
    parser.add_argument("--compile-rounds", type=int, default=2)
    parser.add_argument("--compiler", default="pdflatex")
    parser.add_argument("--title", default="")
    parser.add_argument("--no-reader-artifacts", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()
    source_dir = output_dir / "source"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_kind = copy_or_extract_source(source, source_dir)
    tex_files = discover_tex_files(source_dir, args.tex or [])
    if not tex_files:
        raise RuntimeError(f"No .tex files found in {source_dir}")

    compile_results = []
    if args.compile:
        for tex_file in tex_files:
            compile_results.append(run_compile(tex_file, args.compiler, args.compile_rounds))

    paragraphs_path = output_dir / "latex_paragraphs.json"
    run_paragraph_extraction(source_dir, tex_files, paragraphs_path)

    documents = []
    for tex_file in tex_files:
        pdf_path = tex_file.with_suffix(".pdf")
        synctex_gz = tex_file.with_suffix(".synctex.gz")
        synctex = tex_file.with_suffix(".synctex")
        if not pdf_path.exists():
            continue
        document = {
            "doc": tex_file.stem,
            "label": tex_file.stem,
            "pdf": relative_to_output(pdf_path, output_dir),
        }
        if synctex_gz.exists() or synctex.exists():
            document["synctex"] = relative_to_output(
                synctex_gz if synctex_gz.exists() else synctex,
                output_dir,
            )
        documents.append(document)

    title = args.title or infer_title(tex_files)
    reader_artifacts = None
    if not args.no_reader_artifacts:
        reader_artifacts = write_reader_artifacts(output_dir, title, documents, "latex-primary")

    manifest = {
        "schema_version": "paper-latex-source-prep/1.0",
        "source": str(source),
        "source_kind": source_kind,
        "source_dir": str(source_dir),
        "tex_files": [relative_to_source(path, source_dir) for path in tex_files],
        "compiled": bool(args.compile),
        "compile_results": compile_results,
        "latex_paragraphs": str(paragraphs_path),
        "reader_artifacts": str(reader_artifacts) if reader_artifacts else "",
        "documents": documents,
    }
    manifest_path = output_dir / "latex_source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

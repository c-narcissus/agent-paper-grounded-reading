import argparse
import json
import shutil
import subprocess
from pathlib import Path

import fitz
from markdown import markdown


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "assets" / "reader_template"


def rect_to_list(rect):
    return [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)]


def parse_pdf_arg(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected --pdf key=path")
    key, raw_path = value.split("=", 1)
    return key.strip(), Path(raw_path).expanduser().resolve()


def copy_template(output_dir: Path):
    for asset in TEMPLATE_DIR.iterdir():
        if asset.is_file():
            shutil.copy2(asset, output_dir / asset.name)


def render_report_html(report_markdown: Path, output_dir: Path):
    report_text = report_markdown.read_text(encoding="utf-8")
    html = markdown(
        report_text,
        extensions=["extra", "fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )
    (output_dir / "report.md").write_text(report_text, encoding="utf-8")
    (output_dir / "report.html").write_text(html, encoding="utf-8")


def copy_pdfs(pdf_map, output_dir: Path):
    docs_dir = output_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    copied = {}
    for doc_key, pdf_path in pdf_map.items():
        target_path = docs_dir / f"{doc_key}.pdf"
        shutil.copy2(pdf_path, target_path)
        copied[doc_key] = f"./docs/{target_path.name}"
    return copied


def render_doc(doc_key: str, pdf_path: Path, rendered_dir: Path, zoom: float = 1.8):
    doc = fitz.open(pdf_path)
    doc_dir = rendered_dir / doc_key
    doc_dir.mkdir(parents=True, exist_ok=True)

    pages = []
    matrix = fitz.Matrix(zoom, zoom)
    for page_index in range(doc.page_count):
        page = doc[page_index]
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image_name = f"page-{page_index + 1:03d}.png"
        image_path = doc_dir / image_name
        pix.save(image_path)
        pages.append(
            {
                "number": page_index + 1,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "image": f"./rendered/{doc_key}/{image_name}",
            }
        )
    doc.close()
    return {"pages": pages}


def build_page_manifest(pdf_map, output_dir: Path):
    rendered_dir = output_dir / "rendered"
    manifest = {}
    for doc_key, pdf_path in pdf_map.items():
        manifest[doc_key] = render_doc(doc_key, pdf_path, rendered_dir)
    (output_dir / "page-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def load_paragraph_lookup(paragraphs_path: Path):
    payload = json.loads(paragraphs_path.read_text(encoding="utf-8"))
    return {entry["paragraph_id"]: entry for entry in payload.get("paragraphs", [])}


def infer_synctex_path(pdf_path: Path):
    candidates = [pdf_path.with_suffix(".synctex.gz"), pdf_path.with_suffix(".synctex")]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise RuntimeError(
        f"Missing SyncTeX file for {pdf_path.name}. Recompile the PDF with -synctex=1 or pass --synctex."
    )


def build_synctex_map(pdf_map, synctex_args):
    explicit = dict(synctex_args or [])
    synctex_map = {}
    for doc_key, pdf_path in pdf_map.items():
        synctex_map[doc_key] = explicit.get(doc_key) or infer_synctex_path(pdf_path)
    return synctex_map


def resolve_manifest_path(base_dir: Path, value):
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def load_artifact_manifest(manifest_path: Path):
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_dir = manifest_path.parent

    report_entry = payload.get("report", {})
    report_markdown = report_entry.get("markdown") or payload.get("report_path")
    report_pdf = report_entry.get("pdf") or payload.get("report_pdf")

    traceability_path = (
        payload.get("traceability_manifest")
        or payload.get("traceability")
        or payload.get("manifest")
    )
    paragraphs_path = (
        payload.get("latex_paragraphs")
        or payload.get("paragraphs")
        or payload.get("paragraph_index")
    )

    pdf_map = {}
    synctex_args = []
    for document in payload.get("documents", []):
        doc_key = document.get("doc") or document.get("key") or document.get("id")
        pdf_path = document.get("pdf")
        if not doc_key or not pdf_path:
            continue
        pdf_map[str(doc_key)] = resolve_manifest_path(base_dir, pdf_path)
        synctex_path = document.get("synctex")
        if synctex_path:
            synctex_args.append((str(doc_key), resolve_manifest_path(base_dir, synctex_path)))

    return {
        "report": resolve_manifest_path(base_dir, report_markdown),
        "report_pdf": resolve_manifest_path(base_dir, report_pdf),
        "traceability": resolve_manifest_path(base_dir, traceability_path),
        "paragraphs": resolve_manifest_path(base_dir, paragraphs_path),
        "pdf_map": pdf_map,
        "synctex_args": synctex_args,
        "output": resolve_manifest_path(base_dir, payload.get("reader_output")),
    }


def search_snippet(doc, snippet: str, page_hint=None):
    ordered_pages = list(range(doc.page_count))
    if page_hint and 1 <= page_hint <= doc.page_count:
        hint_index = page_hint - 1
        ordered_pages = [hint_index] + [index for index in ordered_pages if index != hint_index]

    for page_index in ordered_pages:
        page = doc[page_index]
        hits = page.search_for(snippet)
        if hits:
            return [{"page": page_index + 1, "rect": rect_to_list(rect)} for rect in hits]
    return []


def parse_synctex_output(stdout: str):
    records = []
    current = None

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("This is SyncTeX") or line.startswith("SyncTeX result"):
            continue
        if line.startswith("Output:"):
            if current:
                records.append(current)
            current = {}
            continue
        if current is None:
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key] = value

    if current:
        records.append(current)

    matches = []
    for record in records:
        try:
            page = int(record["Page"])
            h = float(record["h"])
            v = float(record["v"])
            width = float(record["W"])
            height = float(record["H"])
        except (KeyError, ValueError):
            continue

        top = max(0.0, v - height)
        matches.append(
            {
                "page": page,
                "rect": rect_to_list(fitz.Rect(h, top, h + width, v)),
            }
        )

    return matches


def candidate_line_numbers(paragraph):
    line_start = paragraph.get("line_start")
    line_end = paragraph.get("line_end")
    source_path = paragraph.get("source_path")
    if not line_start or not line_end or not source_path:
        return []

    structural_prefixes = (
        r"\begin{",
        r"\end{",
        r"\label{",
        r"\centering",
        r"\includegraphics",
        r"\hspace",
        r"\vspace",
    )

    source_lines = Path(source_path).read_text(encoding="utf-8").splitlines()
    candidates = []
    for line_number in range(int(line_start), int(line_end) + 1):
        raw_line = source_lines[line_number - 1]
        stripped = raw_line.split("%", 1)[0].strip()
        if not stripped:
            continue
        if stripped.startswith(structural_prefixes):
            continue
        candidates.append(line_number)

    if candidates:
        return candidates
    return list(range(int(line_start), int(line_end) + 1))


def locate_paragraph_with_synctex(paragraph, pdf_path: Path, synctex_path: Path, page_hint=None):
    line_start = paragraph.get("line_start")
    line_end = paragraph.get("line_end")
    source_path = paragraph.get("source_path")
    if not line_start or not line_end or not source_path:
        return []

    matches = []
    for line_number in candidate_line_numbers(paragraph):
        sync_arg = f"{line_number}:1:{source_path}"
        result = subprocess.run(
            ["synctex", "view", "-i", sync_arg, "-o", str(pdf_path), "-d", str(synctex_path.parent)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        matches.extend(parse_synctex_output(result.stdout))

    return dedupe_matches(matches)


def dedupe_matches(matches):
    seen = set()
    unique = []
    for item in matches:
        key = (
            item["page"],
            item["rect"][0],
            item["rect"][1],
            item["rect"][2],
            item["rect"][3],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def filter_synctex_matches(matches, pdf_doc):
    if not matches:
        return []

    filtered = []
    areas = []
    for item in matches:
        page_rect = pdf_doc[item["page"] - 1].rect
        x0, y0, x1, y1 = item["rect"]
        width = max(0.0, x1 - x0)
        height = max(0.0, y1 - y0)
        area = width * height

        if width <= 0 or height <= 0:
            continue
        if width > page_rect.width * 1.1:
            continue
        if height > page_rect.height * 0.45:
            continue

        filtered.append(item)
        areas.append((item, area, page_rect.width * page_rect.height))

    if not filtered:
        return dedupe_matches(matches)

    if any(area < page_area * 0.08 for _, area, page_area in areas):
        filtered = [item for item, area, page_area in areas if area < page_area * 0.18]

    return dedupe_matches(filtered)


def build_evidence_map(traceability_path: Path, paragraph_lookup, pdf_map, synctex_map, output_dir: Path):
    traceability = json.loads(traceability_path.read_text(encoding="utf-8"))
    docs = {doc_key: fitz.open(pdf_path) for doc_key, pdf_path in pdf_map.items()}

    claims_out = {}
    try:
        for claim in traceability.get("claims", []):
            claim_id = claim["claim_id"]
            claim_out = {
                "claim_id": claim_id,
                "section_id": str(claim["section_id"]),
                "section_title": claim["section_title"],
                "claim_text": claim["claim_text"],
                "evidence": [],
            }

            for evidence in claim.get("evidence", []):
                doc_key = evidence["doc"]
                if doc_key not in docs:
                    raise RuntimeError(f"Unknown doc key in evidence: {doc_key}")

                paragraph = paragraph_lookup.get(evidence.get("paragraph_id"), {})
                matches = []
                match_source = "pdf-search"

                if paragraph and not str(evidence.get("paragraph_id", "")).startswith("pdf::"):
                    matches = locate_paragraph_with_synctex(
                        paragraph=paragraph,
                        pdf_path=pdf_map[doc_key],
                        synctex_path=synctex_map[doc_key],
                        page_hint=evidence.get("page_hint"),
                    )
                    if matches:
                        matches = filter_synctex_matches(matches, docs[doc_key])
                        match_source = "synctex"

                if not matches:
                    for snippet in evidence.get("locator_snippets", []):
                        found = search_snippet(docs[doc_key], snippet, evidence.get("page_hint"))
                        if not found:
                            raise RuntimeError(
                                f"Failed to locate evidence for {claim_id}/{evidence.get('evidence_id')}: {snippet!r}"
                            )
                        matches.extend(found)

                claim_out["evidence"].append(
                    {
                        "evidence_id": evidence["evidence_id"],
                        "doc": doc_key,
                        "quote": evidence["quote"],
                        "relation": evidence.get("relation", "direct"),
                        "paragraph_id": evidence.get("paragraph_id", ""),
                        "tex_file": paragraph.get("tex_file", ""),
                        "section_path": paragraph.get("section_path", []),
                        "paragraph_text": paragraph.get("text", evidence.get("notes", "")),
                        "line_start": paragraph.get("line_start"),
                        "line_end": paragraph.get("line_end"),
                        "match_source": match_source,
                        "matches": dedupe_matches(matches),
                    }
                )

            claims_out[claim_id] = claim_out
    finally:
        for doc in docs.values():
            doc.close()

    payload = {
        "paper": traceability.get("paper", {}),
        "claims": claims_out,
    }
    (output_dir / "evidence-map.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    shutil.copy2(traceability_path, output_dir / "traceability.json")
    return traceability


def write_bundle_config(output_dir: Path, title: str, copied_pdfs, report_pdf_path=None):
    links = [
        {"label": "Report Markdown", "href": "./report.md"},
        {"label": "Traceability JSON", "href": "./traceability.json"},
        {"label": "Paragraph Index", "href": "./latex-paragraphs.json"},
        {"label": "Reader Artifacts", "href": "./reader-artifacts.json"},
    ]
    if report_pdf_path:
        links.insert(1, {"label": "Report PDF", "href": "./report.pdf"})

    for doc_key, pdf_href in copied_pdfs.items():
        label = "Supplementary PDF" if doc_key.lower().startswith("supp") else f"{doc_key.title()} PDF"
        links.append({"label": label, "href": pdf_href})

    config = {
        "title": title,
        "default_doc": "main" if "main" in copied_pdfs else next(iter(copied_pdfs)),
        "documents": {
            doc_key: {
                "label": "Supplementary" if doc_key.lower().startswith("supp") else doc_key.title(),
                "pdf": pdf_href,
            }
            for doc_key, pdf_href in copied_pdfs.items()
        },
        "links": links,
    }
    (output_dir / "bundle-config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_bundle_artifact_manifest(output_dir: Path, traceability, copied_pdfs, report_pdf_path=None, source_manifest=False):
    report = {"markdown": "report.md"}
    if report_pdf_path:
        report["pdf"] = "report.pdf"

    payload = {
        "schema_version": "paper-reader-artifacts/1.0",
        "paper": traceability.get("paper", {}),
        "report": report,
        "traceability_manifest": "traceability.json",
        "latex_paragraphs": "latex-paragraphs.json",
        "documents": [
            {
                "doc": doc_key,
                "label": "Supplementary" if doc_key.lower().startswith("supp") else doc_key.title(),
                "pdf": pdf_href,
            }
            for doc_key, pdf_href in copied_pdfs.items()
        ],
        "reader_output": ".",
    }
    if source_manifest:
        payload["source_artifact_manifest"] = "source-reader-artifacts.json"

    (output_dir / "reader-artifacts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-manifest")
    parser.add_argument("--report")
    parser.add_argument("--traceability")
    parser.add_argument("--paragraphs")
    parser.add_argument("--pdf", action="append", type=parse_pdf_arg)
    parser.add_argument("--synctex", action="append", type=parse_pdf_arg)
    parser.add_argument("--output")
    parser.add_argument("--report-pdf")
    args = parser.parse_args()

    manifest_config = {}
    artifact_manifest_path = None
    if args.artifact_manifest:
        artifact_manifest_path = Path(args.artifact_manifest).expanduser().resolve()
        manifest_config = load_artifact_manifest(artifact_manifest_path)

    report_path = Path(args.report).expanduser().resolve() if args.report else manifest_config.get("report")
    traceability_path = (
        Path(args.traceability).expanduser().resolve()
        if args.traceability
        else manifest_config.get("traceability")
    )
    paragraphs_path = (
        Path(args.paragraphs).expanduser().resolve()
        if args.paragraphs
        else manifest_config.get("paragraphs")
    )
    output_dir = Path(args.output).expanduser().resolve() if args.output else manifest_config.get("output")

    pdf_map = dict(args.pdf or []) if args.pdf else manifest_config.get("pdf_map", {})
    synctex_args = list(manifest_config.get("synctex_args", []))
    if args.synctex:
        synctex_args.extend(args.synctex)

    report_pdf_arg = args.report_pdf or manifest_config.get("report_pdf")

    missing = []
    if not report_path:
        missing.append("--report or report.markdown in --artifact-manifest")
    if not traceability_path:
        missing.append("--traceability or traceability_manifest in --artifact-manifest")
    if not paragraphs_path:
        missing.append("--paragraphs or latex_paragraphs in --artifact-manifest")
    if not pdf_map:
        missing.append("--pdf or documents[] in --artifact-manifest")
    if not output_dir:
        missing.append("--output or reader_output in --artifact-manifest")
    if missing:
        raise SystemExit("Missing required inputs: " + ", ".join(missing))

    output_dir.mkdir(parents=True, exist_ok=True)

    synctex_map = build_synctex_map(pdf_map, synctex_args)
    paragraph_lookup = load_paragraph_lookup(paragraphs_path)

    copy_template(output_dir)
    render_report_html(report_path, output_dir)
    copied_pdfs = copy_pdfs(pdf_map, output_dir)
    build_page_manifest(pdf_map, output_dir)
    traceability = build_evidence_map(traceability_path, paragraph_lookup, pdf_map, synctex_map, output_dir)
    shutil.copy2(paragraphs_path, output_dir / "latex-paragraphs.json")

    report_pdf_path = None
    if report_pdf_arg:
        source_report_pdf = Path(report_pdf_arg).expanduser().resolve()
        report_pdf_path = output_dir / "report.pdf"
        shutil.copy2(source_report_pdf, report_pdf_path)

    if artifact_manifest_path:
        shutil.copy2(artifact_manifest_path, output_dir / "source-reader-artifacts.json")

    write_bundle_config(
        output_dir=output_dir,
        title=traceability.get("paper", {}).get("title", "Paper Evidence Reader"),
        copied_pdfs=copied_pdfs,
        report_pdf_path=report_pdf_path,
    )
    write_bundle_artifact_manifest(
        output_dir=output_dir,
        traceability=traceability,
        copied_pdfs=copied_pdfs,
        report_pdf_path=report_pdf_path,
        source_manifest=artifact_manifest_path is not None,
    )

    print(output_dir)


if __name__ == "__main__":
    main()

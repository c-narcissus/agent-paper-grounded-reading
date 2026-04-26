import argparse
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import fitz
from markdown import markdown

try:
    from latex2mathml.converter import convert as latex_to_mathml
except ImportError:
    latex_to_mathml = None


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "assets" / "reader_template"
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
FENCED_CODE_BLOCK_PATTERN = re.compile(r"(?ms)^(```|~~~)[^\n]*\n.*?^\1\s*$")
CODE_HTML_PATTERN = re.compile(r"<code>(.*?)</code>", re.DOTALL)
DELIMITED_MATH_PATTERN = re.compile(
    r"(?<!\\)\$\$(.+?)(?<!\\)\$\$|(?<!\\)\$(.+?)(?<!\\)\$|\\\[(.+?)\\\]|\\\((.+?)\\\)",
    re.DOTALL,
)
LATEX_MATH_ENV_PATTERN = re.compile(
    r"\\begin\{(?P<env>equation\*?|align\*?|gather\*?|multline\*?)\}"
    r"(?P<body>.*?)"
    r"\\end\{(?P=env)\}",
    re.DOTALL,
)
LATEX_BEGIN_END_PATTERN = re.compile(r"\\(?:begin|end)\{[^{}]+\}(?:\[[^\]]*\])?")
LATEX_ARG_TEXT_COMMAND_PATTERN = re.compile(
    r"\\(?:textbf|textit|emph|text|mathrm|mathbf|operatorname|caption|footnote)\s*\{([^{}]*)\}"
)
LATEX_REF_COMMAND_PATTERN = re.compile(r"\\(?:ref|eqref|cite|citep|citet)\s*\{([^{}]*)\}")
BLOCK_MATH_AFTER_BREAK_PATTERN = re.compile(
    r"(<br\s*/?>\s*)(<span class=\"math-(?:rendered|fallback) math-(?:rendered|fallback)--inline\".*?</span>)",
    re.DOTALL,
)
STANDALONE_INLINE_MATH_PATTERN = re.compile(
    r"(<p>\s*)(<span class=\"math-(?:rendered|fallback) math-(?:rendered|fallback)--inline\".*?</span>)(\s*</p>)",
    re.DOTALL,
)
LATEX_COMMAND_PATTERN = re.compile(r"\\[A-Za-z]+")
BASIC_SYMBOL_PATTERN = re.compile(r"^[A-Za-z](?:[_^][A-Za-z0-9]+)*$")
GREEK_SYMBOL_PATTERN = re.compile(
    r"^(alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|"
    r"lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega)(?:[_^][A-Za-z0-9]+)*$"
)
GREEK_SYMBOLS = {
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "varepsilon",
    "zeta",
    "eta",
    "theta",
    "vartheta",
    "iota",
    "kappa",
    "lambda",
    "mu",
    "nu",
    "xi",
    "pi",
    "rho",
    "sigma",
    "tau",
    "upsilon",
    "phi",
    "varphi",
    "chi",
    "psi",
    "omega",
}
ALLOW_MATH_FALLBACK = False


def rect_to_list(rect):
    return [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)]


def rect_from_list(values):
    return fitz.Rect(values[0], values[1], values[2], values[3])


def union_rects(rects):
    if not rects:
        return None

    merged = fitz.Rect(rects[0])
    for rect in rects[1:]:
        merged |= fitz.Rect(rect)
    return merged


def clamp_rect_to_page(rect, page_rect):
    return fitz.Rect(
        max(page_rect.x0, rect.x0),
        max(page_rect.y0, rect.y0),
        min(page_rect.x1, rect.x1),
        min(page_rect.y1, rect.y1),
    )


def parse_pdf_arg(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected --pdf key=path")
    key, raw_path = value.split("=", 1)
    return key.strip(), Path(raw_path).expanduser().resolve()


def copy_template(output_dir: Path):
    for asset in TEMPLATE_DIR.iterdir():
        if asset.is_file():
            shutil.copy2(asset, output_dir / asset.name)


def looks_like_latex_math(value: str):
    stripped = value.strip()
    if not stripped:
        return False
    if LATEX_COMMAND_PATTERN.search(stripped):
        return True
    if BASIC_SYMBOL_PATTERN.fullmatch(stripped):
        return True
    if GREEK_SYMBOL_PATTERN.fullmatch(stripped):
        return True
    if any(token in stripped for token in ("_{", "^{", "_{", "^")) and any(
        char.isalpha() for char in stripped
    ):
        return True
    if "=" in stripped and any(char in stripped for char in "_^{}()"):
        return True
    if "{" in stripped and "}" in stripped and any(char in stripped for char in "_^"):
        return True
    return False


def normalize_latex_math(latex: str):
    normalized = latex.strip()
    if not normalized:
        return normalized

    # Reports often use inline code like `G_i`, `phi_i`, or `alpha`.
    # Convert these into LaTeX that renders like a Word equation.
    for name in sorted(GREEK_SYMBOLS, key=len, reverse=True):
        normalized = re.sub(rf"(?<!\\)(?<![A-Za-z]){name}(?=(_|\^|$))", rf"\\{name}", normalized)

    normalized = re.sub(r"_([A-Za-z0-9]{2,})(?![A-Za-z0-9{])", r"_{\1}", normalized)
    normalized = re.sub(r"\^([A-Za-z0-9]{2,})(?![A-Za-z0-9{])", r"^{\1}", normalized)
    return normalized


def render_math_markup(latex: str, display: str = "inline"):
    cleaned = normalize_latex_math(latex)
    escaped = html.escape(cleaned, quote=True)
    if not cleaned:
        return ""

    if latex_to_mathml is None:
        if not ALLOW_MATH_FALLBACK:
            raise RuntimeError(
                "latex2mathml is required to render reader math. Install requirements.txt "
                "or rerun with --allow-math-fallback only if raw-code fallback is acceptable."
            )
        return (
            f'<span class="math-fallback math-fallback--{display}" data-latex="{escaped}">'
            f"<code>{escaped}</code></span>"
        )

    try:
        mathml = latex_to_mathml(cleaned, display=display)
    except Exception as exc:
        if not ALLOW_MATH_FALLBACK:
            raise RuntimeError(f"Failed to render LaTeX math {cleaned!r}: {exc}") from exc
        return (
            f'<span class="math-fallback math-fallback--{display}" data-latex="{escaped}">'
            f"<code>{escaped}</code></span>"
        )

    return (
        f'<span class="math-rendered math-rendered--{display}" data-latex="{escaped}">'
        f"{mathml}</span>"
    )


def promote_math_markup_to_block(markup: str):
    return (
        markup.replace("math-rendered--inline", "math-rendered--block", 1)
        .replace("math-fallback--inline", "math-fallback--block", 1)
        .replace('display="inline"', 'display="block"', 1)
    )


def render_delimited_math(text: str):
    rendered = []
    last_index = 0

    for match in DELIMITED_MATH_PATTERN.finditer(text):
        start, end = match.span()
        if start > last_index:
            rendered.append(html.escape(text[last_index:start]).replace("\n", "<br>\n"))

        latex = next(group for group in match.groups() if group is not None)
        display = "block" if match.group(1) is not None or match.group(3) is not None else "inline"
        rendered.append(render_math_markup(latex, display))
        last_index = end

    if last_index < len(text):
        rendered.append(html.escape(text[last_index:]).replace("\n", "<br>\n"))

    return "".join(rendered) if rendered else html.escape(text).replace("\n", "<br>\n")


def render_text_with_math(text: str):
    raw_text = text or ""
    placeholders = {}

    def replace_inline_code(match):
        code_value = match.group(1)
        if not looks_like_latex_math(code_value):
            return match.group(0)
        token = f"@@MATH_CODE_{len(placeholders)}@@"
        placeholders[token] = render_math_markup(code_value, "inline")
        return token

    intermediate = INLINE_CODE_PATTERN.sub(replace_inline_code, raw_text)
    rendered = render_delimited_math(intermediate)
    for token, markup in placeholders.items():
        rendered = rendered.replace(token, markup)
    return rendered


def clean_math_environment_body(body: str):
    cleaned = body or ""
    cleaned = re.sub(r"\\label\{[^{}]*\}", "", cleaned)
    cleaned = re.sub(r"\\(?:begin|end)\{(?:aligned|split|matrix|pmatrix|bmatrix|cases)\}", "", cleaned)
    cleaned = cleaned.replace("&", " ")
    cleaned = re.sub(r"\\\\+", r" ; ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def sanitize_latex_source_text(text: str):
    sanitized = text or ""
    sanitized = LATEX_BEGIN_END_PATTERN.sub(" ", sanitized)
    sanitized = re.sub(r"\\item\b", " - ", sanitized)
    sanitized = re.sub(r"\\label\{[^{}]*\}", "", sanitized)
    sanitized = LATEX_REF_COMMAND_PATTERN.sub(r"\1", sanitized)

    previous = None
    while previous != sanitized:
        previous = sanitized
        sanitized = LATEX_ARG_TEXT_COMMAND_PATTERN.sub(r"\1", sanitized)
        sanitized = re.sub(r"\\[A-Za-z]+\*?\s*(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", sanitized)

    replacements = {
        r"\%": "%",
        r"\_": "_",
        r"\&": "&",
        r"\#": "#",
        r"\{": "{",
        r"\}": "}",
        r"``": '"',
        r"''": '"',
    }
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target)

    sanitized = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", sanitized)
    sanitized = sanitized.replace("\\\\", " ")
    sanitized = sanitized.replace("\\", " ")
    sanitized = sanitized.replace("{", "").replace("}", "")
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized


def render_latex_source_text_with_math(text: str):
    raw_text = text or ""
    placeholders = {}

    def stash_markup(markup: str):
        token = f"@@LATEX_SOURCE_MATH_{len(placeholders)}@@"
        placeholders[token] = markup
        return token

    def replace_math_environment(match):
        latex = clean_math_environment_body(match.group("body"))
        return stash_markup(render_math_markup(latex, "block")) if latex else ""

    protected = LATEX_MATH_ENV_PATTERN.sub(replace_math_environment, raw_text)

    def replace_delimited_math(match):
        latex = next(group for group in match.groups() if group is not None)
        display = "block" if match.group(1) is not None or match.group(3) is not None else "inline"
        return stash_markup(render_math_markup(latex, display))

    protected = DELIMITED_MATH_PATTERN.sub(replace_delimited_math, protected)
    sanitized = sanitize_latex_source_text(protected)
    rendered = html.escape(sanitized).replace("\n", "<br>\n")
    for token, markup in placeholders.items():
        rendered = rendered.replace(token, markup)
    return rendered


def preprocess_report_markdown_math(report_text: str):
    placeholders = {}

    def stash_literal(value: str):
        token = f"@@PAPERREADERLITERAL{len(placeholders)}@@"
        placeholders[token] = value
        return token

    protected = FENCED_CODE_BLOCK_PATTERN.sub(lambda match: stash_literal(match.group(0)), report_text)

    def replace_inline_code(match):
        code_value = match.group(1)
        if looks_like_latex_math(code_value):
            return render_math_markup(code_value, "inline")
        return stash_literal(match.group(0))

    converted = INLINE_CODE_PATTERN.sub(replace_inline_code, protected)

    def replace_delimited_math(match):
        latex = next(group for group in match.groups() if group is not None)
        display = "block" if match.group(1) is not None or match.group(3) is not None else "inline"
        return render_math_markup(latex, display)

    converted = DELIMITED_MATH_PATTERN.sub(replace_delimited_math, converted)
    for token, literal in placeholders.items():
        converted = converted.replace(token, literal)
    return converted


def convert_report_html_math(report_html: str):
    def replace_code_tag(match):
        code_value = html.unescape(match.group(1))
        if not looks_like_latex_math(code_value):
            return match.group(0)
        return render_math_markup(code_value, "inline")

    converted = CODE_HTML_PATTERN.sub(replace_code_tag, report_html)
    converted = BLOCK_MATH_AFTER_BREAK_PATTERN.sub(
        lambda match: f"{match.group(1)}{promote_math_markup_to_block(match.group(2))}",
        converted,
    )
    converted = STANDALONE_INLINE_MATH_PATTERN.sub(
        lambda match: f"{match.group(1)}{promote_math_markup_to_block(match.group(2))}{match.group(3)}",
        converted,
    )
    return converted


def render_report_html(report_markdown: Path, output_dir: Path):
    report_text = report_markdown.read_text(encoding="utf-8")
    report_text_for_html = preprocess_report_markdown_math(report_text)
    html = markdown(
        report_text_for_html,
        extensions=["extra", "fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )
    html = convert_report_html_math(html)
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


def copy_optional_artifact(source_path: Path | None, output_dir: Path, target_name: str):
    if not source_path:
        return None
    target_path = output_dir / target_name
    shutil.copy2(source_path, target_path)
    return f"./{target_path.name}"


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


def build_synctex_map(pdf_map, synctex_args, require_synctex=True):
    explicit = dict(synctex_args or [])
    synctex_map = {}
    for doc_key, pdf_path in pdf_map.items():
        if doc_key in explicit:
            synctex_map[doc_key] = explicit[doc_key]
        elif require_synctex:
            synctex_map[doc_key] = infer_synctex_path(pdf_path)
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
        "research_lens": resolve_manifest_path(base_dir, payload.get("research_lens")),
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


def expand_matches_to_paragraph_blocks(matches, pdf_doc, x_padding=10.0, y_padding=6.0):
    grouped = {}
    for match in matches:
        grouped.setdefault(match["page"], []).append(rect_from_list(match["rect"]))

    expanded = []
    for page_number, rects in grouped.items():
        if not rects:
            continue

        page = pdf_doc[page_number - 1]
        page_rect = page.rect
        anchor_rect = union_rects(rects)
        if anchor_rect is None:
            continue

        search_rect = fitz.Rect(anchor_rect)
        search_rect.x0 -= x_padding
        search_rect.x1 += x_padding
        search_rect.y0 -= y_padding
        search_rect.y1 += y_padding
        search_rect = clamp_rect_to_page(search_rect, page_rect)

        block_rects = []
        for block in page.get_text("blocks"):
            if len(block) < 5:
                continue
            x0, y0, x1, y1, text = block[:5]
            block_type = block[6] if len(block) > 6 else 0
            if block_type != 0:
                continue
            if not str(text).strip():
                continue

            block_rect = fitz.Rect(x0, y0, x1, y1)
            if block_rect.intersects(search_rect):
                block_rects.append(block_rect)

        granularity = "paragraph-block"
        merged_rect = union_rects(block_rects)
        if merged_rect is None:
            granularity = "line-cluster"
            merged_rect = anchor_rect

        padding = 2.0 if granularity == "paragraph-block" else 1.0
        merged_rect = fitz.Rect(merged_rect)
        merged_rect.x0 -= padding
        merged_rect.x1 += padding
        merged_rect.y0 -= padding
        merged_rect.y1 += padding
        merged_rect = clamp_rect_to_page(merged_rect, page_rect)

        expanded.append(
            {
                "page": page_number,
                "rect": rect_to_list(merged_rect),
                "granularity": granularity,
            }
        )

    return dedupe_matches(expanded)


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
                "claim_text_html": render_text_with_math(claim.get("claim_text", "")),
                "interpretation_type": claim.get("interpretation_type", ""),
                "research_role": claim.get("research_role", ""),
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
                    matches = expand_matches_to_paragraph_blocks(matches, docs[doc_key])
                else:
                    matches = expand_matches_to_paragraph_blocks(matches, docs[doc_key])

                claim_out["evidence"].append(
                    {
                        "evidence_id": evidence["evidence_id"],
                        "doc": doc_key,
                        "quote": evidence["quote"],
                        "quote_html": render_text_with_math(evidence.get("quote", "")),
                        "relation": evidence.get("relation", "direct"),
                        "paragraph_id": evidence.get("paragraph_id", ""),
                        "tex_file": paragraph.get("tex_file", ""),
                        "section_path": paragraph.get("section_path", []),
                        "paragraph_text": paragraph.get("text", evidence.get("notes", "")),
                        "paragraph_html": render_latex_source_text_with_math(
                            paragraph.get("text", evidence.get("notes", ""))
                        ),
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


def write_bundle_config(output_dir: Path, title: str, copied_pdfs, report_pdf_path=None, research_lens_href=None):
    links = [
        {"label": "Report Markdown", "href": "./report.md"},
        {"label": "Traceability JSON", "href": "./traceability.json"},
        {"label": "Reader Artifacts", "href": "./reader-artifacts.json"},
    ]
    paragraph_index_path = output_dir / "latex-paragraphs.json"
    if paragraph_index_path.exists():
        links.insert(2, {"label": "Paragraph Index", "href": "./latex-paragraphs.json"})
    if research_lens_href:
        links.insert(3 if paragraph_index_path.exists() else 2, {"label": "Research Lens", "href": research_lens_href})
    if report_pdf_path:
        links.insert(1, {"label": "Report PDF", "href": "./report.pdf"})

    for doc_key, pdf_href in copied_pdfs.items():
        label = "Supplementary PDF" if doc_key.lower().startswith("supp") else f"{doc_key.title()} PDF"
        links.append({"label": label, "href": pdf_href})

    config = {
        "title": title,
        "subtitle": "Trace grounded claims, inspect evidence, and mine reusable research patterns.",
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
    if research_lens_href:
        config["research_lens"] = research_lens_href
    (output_dir / "bundle-config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_bundle_artifact_manifest(
    output_dir: Path,
    traceability,
    copied_pdfs,
    report_pdf_path=None,
    source_manifest=False,
    research_lens_href=None,
):
    report = {"markdown": "report.md"}
    if report_pdf_path:
        report["pdf"] = "report.pdf"

    payload = {
        "schema_version": "paper-reader-artifacts/1.0",
        "paper": traceability.get("paper", {}),
        "report": report,
        "traceability_manifest": "traceability.json",
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
    if (output_dir / "latex-paragraphs.json").exists():
        payload["paragraph_index"] = "latex-paragraphs.json"
        payload["latex_paragraphs"] = "latex-paragraphs.json"
    if research_lens_href:
        payload["research_lens"] = "research-lens.json"
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
    parser.add_argument(
        "--allow-math-fallback",
        action="store_true",
        help="Allow raw-code math fallback when latex2mathml is missing or cannot render a formula.",
    )
    args = parser.parse_args()

    global ALLOW_MATH_FALLBACK
    ALLOW_MATH_FALLBACK = args.allow_math_fallback

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
    research_lens_path = manifest_config.get("research_lens")

    missing = []
    if not report_path:
        missing.append("--report or report.markdown in --artifact-manifest")
    if not traceability_path:
        missing.append("--traceability or traceability_manifest in --artifact-manifest")
    if not pdf_map:
        missing.append("--pdf or documents[] in --artifact-manifest")
    if not output_dir:
        missing.append("--output or reader_output in --artifact-manifest")
    if missing:
        raise SystemExit("Missing required inputs: " + ", ".join(missing))

    output_dir.mkdir(parents=True, exist_ok=True)

    paragraph_lookup = load_paragraph_lookup(paragraphs_path) if paragraphs_path else {}
    synctex_map = build_synctex_map(
        pdf_map,
        synctex_args,
        require_synctex=bool(paragraph_lookup),
    )

    copy_template(output_dir)
    render_report_html(report_path, output_dir)
    copied_pdfs = copy_pdfs(pdf_map, output_dir)
    build_page_manifest(pdf_map, output_dir)
    traceability = build_evidence_map(traceability_path, paragraph_lookup, pdf_map, synctex_map, output_dir)
    if paragraphs_path:
        shutil.copy2(paragraphs_path, output_dir / "latex-paragraphs.json")
    research_lens_href = copy_optional_artifact(research_lens_path, output_dir, "research-lens.json")

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
        research_lens_href=research_lens_href,
    )
    write_bundle_artifact_manifest(
        output_dir=output_dir,
        traceability=traceability,
        copied_pdfs=copied_pdfs,
        report_pdf_path=report_pdf_path,
        source_manifest=artifact_manifest_path is not None,
        research_lens_href=research_lens_href,
    )

    print(output_dir)


if __name__ == "__main__":
    main()

import argparse
import json
import shutil
from pathlib import Path

import fitz


def render_page(page, output_path: Path, zoom: float):
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    pixmap.save(output_path)


def block_to_record(block):
    x0, y0, x1, y1, text = block[:5]
    block_type = block[6] if len(block) > 6 else 0
    return {
        "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
        "type": int(block_type),
        "text": str(text).strip(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Prepare reusable PDF-only source artifacts for grounded paper reading."
    )
    parser.add_argument("--pdf", required=True, help="Input paper PDF.")
    parser.add_argument("--output", required=True, help="Output directory for extracted PDF artifacts.")
    parser.add_argument("--doc-key", default="paper", help="Document key used in traceability rows.")
    parser.add_argument("--text-output", default=None, help="Text output filename or path.")
    parser.add_argument("--pages-output", default="pdf_pages.json", help="Page/block JSON filename or path.")
    parser.add_argument("--preview-dir", default="page_previews", help="Rendered page preview directory.")
    parser.add_argument("--zoom", type=float, default=1.5, help="Preview render zoom.")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional page limit for quick tests.")
    parser.add_argument("--skip-render", action="store_true", help="Do not render page preview PNGs.")
    parser.add_argument("--copy-pdf", action="store_true", help="Copy the source PDF into the output directory.")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    text_output = Path(args.text_output) if args.text_output else Path(f"{pdf_path.stem}_pdf_text.txt")
    if not text_output.is_absolute():
        text_output = output_dir / text_output

    pages_output = Path(args.pages_output)
    if not pages_output.is_absolute():
        pages_output = output_dir / pages_output

    preview_root = Path(args.preview_dir)
    if not preview_root.is_absolute():
        preview_root = output_dir / preview_root
    preview_doc_dir = preview_root / args.doc_key

    doc = fitz.open(pdf_path)
    total_page_count = doc.page_count
    page_count = total_page_count if args.max_pages is None else min(total_page_count, args.max_pages)
    pages = []
    text_chunks = []

    if not args.skip_render:
        preview_doc_dir.mkdir(parents=True, exist_ok=True)

    try:
        for page_index in range(page_count):
            page = doc[page_index]
            page_number = page_index + 1
            text = page.get_text("text")
            blocks = [
                block_to_record(block)
                for block in page.get_text("blocks")
                if len(block) >= 5 and str(block[4]).strip()
            ]

            preview_href = None
            if not args.skip_render:
                image_name = f"page-{page_number:03d}.png"
                render_page(page, preview_doc_dir / image_name, args.zoom)
                preview_href = str((preview_doc_dir / image_name).relative_to(output_dir)).replace("\\", "/")

            text_chunks.append(f"--- Page {page_number} ---\n{text.rstrip()}\n")
            pages.append(
                {
                    "doc": args.doc_key,
                    "page": page_number,
                    "width": round(page.rect.width, 2),
                    "height": round(page.rect.height, 2),
                    "text": text,
                    "blocks": blocks,
                    "preview": preview_href,
                }
            )
    finally:
        doc.close()

    text_output.write_text("\n".join(text_chunks).rstrip() + "\n", encoding="utf-8")
    payload = {
        "schema_version": "paper-pdf-source/1.0",
        "doc": args.doc_key,
        "source_pdf": str(pdf_path),
        "page_count": total_page_count,
        "extracted_pages": page_count,
        "text_output": str(text_output),
        "pages": pages,
    }
    pages_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    copied_pdf = None
    if args.copy_pdf:
        copied_pdf = output_dir / pdf_path.name
        if copied_pdf != pdf_path:
            shutil.copy2(pdf_path, copied_pdf)

    print(
        json.dumps(
            {
                "status": "ok",
                "doc": args.doc_key,
                "pages": page_count,
                "text_output": str(text_output),
                "pages_output": str(pages_output),
                "preview_dir": None if args.skip_render else str(preview_doc_dir),
                "copied_pdf": str(copied_pdf) if copied_pdf else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

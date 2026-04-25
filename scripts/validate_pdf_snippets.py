import argparse
import json
import sys
from pathlib import Path

import fitz


def parse_pdf_arg(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected --pdf key=path")
    key, raw_path = value.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError("PDF key cannot be empty")
    return key, Path(raw_path).expanduser().resolve()


def search_exact(doc, snippet, page_hint=None):
    page_order = list(range(doc.page_count))
    if page_hint and 1 <= page_hint <= doc.page_count:
        hinted = page_hint - 1
        page_order = [hinted] + [index for index in page_order if index != hinted]

    hits = []
    for page_index in page_order:
        page_hits = doc[page_index].search_for(snippet)
        if page_hits:
            hits.append(
                {
                    "page": page_index + 1,
                    "hit_count": len(page_hits),
                    "page_hint_match": page_hint == page_index + 1,
                }
            )
    return hits


def main():
    parser = argparse.ArgumentParser(
        description="Validate that PDF fallback locator_snippets are searchable by PyMuPDF."
    )
    parser.add_argument("--traceability", required=True, help="traceability_manifest.json path.")
    parser.add_argument("--pdf", action="append", required=True, type=parse_pdf_arg, help="Document map entry key=path.")
    parser.add_argument("--output", help="Optional JSON audit output path.")
    parser.add_argument(
        "--strict-page-hint",
        action="store_true",
        help="Fail when a snippet is found elsewhere but not on its page_hint.",
    )
    args = parser.parse_args()

    traceability_path = Path(args.traceability).expanduser().resolve()
    pdf_map = dict(args.pdf or [])
    docs = {doc_key: fitz.open(pdf_path) for doc_key, pdf_path in pdf_map.items()}

    manifest = json.loads(traceability_path.read_text(encoding="utf-8"))
    checked = 0
    missing = []
    wrong_page = []
    rows = []

    try:
        for claim in manifest.get("claims", []):
            claim_id = claim.get("claim_id", "<missing>")
            for evidence in claim.get("evidence", []):
                evidence_id = evidence.get("evidence_id", "<missing>")
                doc_key = evidence.get("doc")
                if doc_key not in docs:
                    continue
                page_hint = evidence.get("page_hint")
                for snippet in evidence.get("locator_snippets") or []:
                    checked += 1
                    hits = search_exact(docs[doc_key], snippet, page_hint)
                    row = {
                        "claim_id": claim_id,
                        "evidence_id": evidence_id,
                        "doc": doc_key,
                        "page_hint": page_hint,
                        "snippet": snippet,
                        "hits": hits,
                    }
                    rows.append(row)
                    if not hits:
                        missing.append(row)
                    elif args.strict_page_hint and page_hint and not any(hit["page_hint_match"] for hit in hits):
                        wrong_page.append(row)
    finally:
        for doc in docs.values():
            doc.close()

    status = "ok" if not missing and not wrong_page else "error"
    payload = {
        "status": status,
        "traceability": str(traceability_path),
        "checked_snippets": checked,
        "missing_count": len(missing),
        "wrong_page_count": len(wrong_page),
        "documents": {key: str(path) for key, path in pdf_map.items()},
        "missing": missing,
        "wrong_page": wrong_page,
        "rows": rows,
    }

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": status,
                "checked_snippets": checked,
                "missing_count": len(missing),
                "wrong_page_count": len(wrong_page),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if status != "ok":
        for item in missing[:10]:
            print(
                f"Missing snippet for {item['claim_id']}/{item['evidence_id']}: {item['snippet']!r}",
                file=sys.stderr,
            )
        for item in wrong_page[:10]:
            print(
                f"Snippet not found on page_hint for {item['claim_id']}/{item['evidence_id']}: {item['snippet']!r}",
                file=sys.stderr,
            )
        sys.exit(1)


if __name__ == "__main__":
    main()

import argparse
import json
import re
import sys
from pathlib import Path


CLAIM_PATTERN = re.compile(r"\[(C\d+\.\d+)\]")
ALLOWED_INTERPRETATION_TYPES = {
    "evidence-backed interpretation",
    "plausible inference",
    "speculation",
}


def load_claim_ids(report_path: Path):
    text = report_path.read_text(encoding="utf-8")
    claim_ids = CLAIM_PATTERN.findall(text)
    duplicates = sorted({claim_id for claim_id in claim_ids if claim_ids.count(claim_id) > 1})
    return claim_ids, duplicates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--traceability", required=True)
    parser.add_argument("--paragraphs")
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    traceability_path = Path(args.traceability).resolve()
    paragraphs_path = Path(args.paragraphs).resolve() if args.paragraphs else None

    report_claim_ids, duplicate_report_claims = load_claim_ids(report_path)
    manifest = json.loads(traceability_path.read_text(encoding="utf-8"))
    paragraph_ids = set()
    if paragraphs_path:
        paragraph_bundle = json.loads(paragraphs_path.read_text(encoding="utf-8"))
        paragraph_ids = {entry["paragraph_id"] for entry in paragraph_bundle.get("paragraphs", [])}

    manifest_claims = manifest.get("claims", [])
    manifest_ids = [claim.get("claim_id") for claim in manifest_claims]
    duplicate_manifest_ids = sorted({claim_id for claim_id in manifest_ids if manifest_ids.count(claim_id) > 1})

    errors = []

    if not report_claim_ids:
        errors.append("No anchored claim IDs like [C1.1] were found in the report.")
    if duplicate_report_claims:
        errors.append(f"Duplicate claim IDs in report: {', '.join(duplicate_report_claims)}")
    if duplicate_manifest_ids:
        errors.append(f"Duplicate claim IDs in manifest: {', '.join(duplicate_manifest_ids)}")

    report_set = set(report_claim_ids)
    manifest_set = set(manifest_ids)

    missing_in_manifest = sorted(report_set - manifest_set)
    if missing_in_manifest:
        errors.append(f"Claims present in report but missing in manifest: {', '.join(missing_in_manifest)}")

    missing_in_report = sorted(manifest_set - report_set)
    if missing_in_report:
        errors.append(f"Claims present in manifest but missing in report: {', '.join(missing_in_report)}")

    for claim in manifest_claims:
        claim_id = claim.get("claim_id", "<missing>")
        section_id = str(claim.get("section_id", ""))
        if section_id and not claim_id.startswith(f"C{section_id}."):
            errors.append(f"{claim_id} does not match section_id={section_id}.")

        if not claim.get("claim_text"):
            errors.append(f"{claim_id} is missing claim_text.")

        interpretation_type = claim.get("interpretation_type")
        if interpretation_type and interpretation_type not in ALLOWED_INTERPRETATION_TYPES:
            errors.append(
                f"{claim_id} has invalid interpretation_type {interpretation_type!r}; "
                "expected evidence-backed interpretation, plausible inference, or speculation."
            )

        evidence_rows = claim.get("evidence", [])
        if not evidence_rows:
            errors.append(f"{claim_id} has no evidence rows.")
            continue

        for evidence in evidence_rows:
            evidence_id = evidence.get("evidence_id", "<missing>")
            paragraph_id = evidence.get("paragraph_id")
            snippets = evidence.get("locator_snippets") or []

            if not paragraph_id:
                errors.append(f"{claim_id}/{evidence_id} is missing paragraph_id.")
            elif paragraph_id.startswith("pdf::"):
                pass
            elif not paragraphs_path:
                errors.append(
                    f"{claim_id}/{evidence_id} references {paragraph_id}, but no --paragraphs index was provided."
                )
            elif paragraph_id not in paragraph_ids:
                errors.append(f"{claim_id}/{evidence_id} references unknown paragraph_id {paragraph_id}.")

            if not snippets:
                errors.append(f"{claim_id}/{evidence_id} is missing locator_snippets.")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        sys.exit(1)

    print(
        json.dumps(
            {
                "report_claims": len(report_set),
                "manifest_claims": len(manifest_claims),
                "paragraph_count": len(paragraph_ids),
                "source_anchor_mode": "mixed-or-structured" if paragraphs_path else "pdf-fallback-only",
                "status": "ok",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

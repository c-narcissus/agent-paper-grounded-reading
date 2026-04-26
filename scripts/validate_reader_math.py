import argparse
import html
import json
import re
import sys
from pathlib import Path


MATH_FALLBACK_PATTERN = re.compile(r"class=[\"'][^\"']*math-fallback")
MATH_RENDERED_PATTERN = re.compile(
    r"<span\b[^>]*class=[\"'][^\"']*math-rendered[^\"']*[\"'][\s\S]*?</span>",
    re.IGNORECASE,
)
DATA_LATEX_PATTERN = re.compile(r"\sdata-latex=(\"[^\"]*\"|'[^']*')", re.IGNORECASE)
SCRIPT_STYLE_PATTERN = re.compile(r"<(script|style)\b[\s\S]*?</\1>", re.IGNORECASE)
PRE_CODE_PATTERN = re.compile(r"<pre\b[\s\S]*?</pre>|<code\b[\s\S]*?</code>", re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>")
RAW_DELIMITER_PATTERNS = [
    re.compile(r"\\\("),
    re.compile(r"\\\["),
    re.compile(r"(?<!\\)\$\$"),
    re.compile(r"(?<!\\)\$[^$\n]{1,240}(?<!\\)\$"),
]
RAW_COMMAND_PATTERN = re.compile(
    r"\\(?:alpha|beta|gamma|delta|epsilon|varepsilon|theta|lambda|mu|pi|phi|psi|omega|"
    r"sum|prod|frac|sqrt|mathbb|mathcal|mathbf|operatorname|text|hat|bar|tilde|"
    r"cdot|times|leq|geq|neq|approx|sim|infty|ell|begin|end)\b"
)


def visible_text_without_rendered_math(html_text: str):
    cleaned = SCRIPT_STYLE_PATTERN.sub(" ", html_text)
    cleaned = MATH_RENDERED_PATTERN.sub(" ", cleaned)
    cleaned = PRE_CODE_PATTERN.sub(" ", cleaned)
    cleaned = DATA_LATEX_PATTERN.sub("", cleaned)
    cleaned = TAG_PATTERN.sub(" ", cleaned)
    return html.unescape(cleaned)


def collect_raw_math_issues(label: str, html_text: str):
    issues = []
    if MATH_FALLBACK_PATTERN.search(html_text):
        issues.append({"source": label, "type": "math-fallback", "sample": "math-fallback"})

    visible = visible_text_without_rendered_math(html_text)
    for pattern in RAW_DELIMITER_PATTERNS:
        match = pattern.search(visible)
        if match:
            issues.append(
                {
                    "source": label,
                    "type": "raw-math-delimiter",
                    "sample": visible[max(0, match.start() - 60) : match.end() + 60],
                }
            )
            break

    command_match = RAW_COMMAND_PATTERN.search(visible)
    if command_match:
        issues.append(
            {
                "source": label,
                "type": "raw-latex-command",
                "sample": visible[max(0, command_match.start() - 60) : command_match.end() + 60],
            }
        )

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Validate that a built reader bundle does not expose raw LaTeX math."
    )
    parser.add_argument("--bundle", required=True, help="Built reader_bundle directory.")
    args = parser.parse_args()

    bundle_dir = Path(args.bundle).expanduser().resolve()
    report_html = bundle_dir / "report.html"
    evidence_map = bundle_dir / "evidence-map.json"

    issues = []
    if not report_html.exists():
        issues.append({"source": str(report_html), "type": "missing-file", "sample": "report.html"})
    else:
        issues.extend(collect_raw_math_issues(str(report_html), report_html.read_text(encoding="utf-8")))

    if evidence_map.exists():
        payload = json.loads(evidence_map.read_text(encoding="utf-8"))
        for claim_id, claim in (payload.get("claims") or {}).items():
            for field in ("claim_text_html",):
                if claim.get(field):
                    issues.extend(collect_raw_math_issues(f"{claim_id}.{field}", claim[field]))
            for evidence in claim.get("evidence") or []:
                evidence_id = evidence.get("evidence_id", "<missing>")
                for field in ("quote_html", "paragraph_html"):
                    if evidence.get(field):
                        issues.extend(
                            collect_raw_math_issues(f"{claim_id}/{evidence_id}.{field}", evidence[field])
                        )

    if issues:
        print(json.dumps({"status": "error", "issue_count": len(issues), "issues": issues[:25]}, indent=2))
        sys.exit(1)

    print(json.dumps({"status": "ok", "bundle": str(bundle_dir), "issue_count": 0}, indent=2))


if __name__ == "__main__":
    main()

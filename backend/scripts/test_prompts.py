"""
Prompt quality evaluator for Northbound Control Tower AI outputs.

Evaluates AI responses against measurable criteria so that prompt iteration
has an objective stop condition rather than subjective review.

Stop criterion: 13/13 criteria passed across two distinct contexts.

Usage:
    python scripts/test_prompts.py --type executive_summary --file output.json
    python scripts/test_prompts.py --type executive_summary --file output.json --strict
    python scripts/test_prompts.py --type executive_summary --file output.json --save

No AI calls are made by this script. No API key is required.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────────

_VALID_RISK_LEVELS = {"critical", "high", "medium", "low"}

_TECH_JARGON = [
    "ec2",
    "s3 bucket",
    "iam policy",
    "terraform",
    "kubectl",
    "ocid",
    "vpc",
    "rds",
    "lambda",
    "cloudformation",
]

_TOTAL_CRITERIA = 13


# ── Core evaluator ─────────────────────────────────────────────────────────────

def check_executive_summary(output: dict[str, Any]) -> list[tuple[str, bool, str]]:
    """Return list of (criterion, passed, detail) — always exactly 13 entries.

    Criteria that depend on nested structure never silently disappear: when a
    parent key is missing the child criterion is still appended as failed.
    """
    results: list[tuple[str, bool, str]] = []
    es = output.get("executive_summary", {})

    # ── 1-4  Required top-level keys ──────────────────────────────────────────
    for key in (
        "overall_posture",
        "business_risk",
        "domain_highlights",
        "recommendations_30_60_90",
    ):
        results.append((f"has {key}", key in es, "missing key" if key not in es else ""))

    # ── 5-7  overall_posture quality ──────────────────────────────────────────
    posture = es.get("overall_posture", {})

    risk_level = posture.get("risk_level", "")
    results.append((
        "valid risk_level",
        risk_level in _VALID_RISK_LEVELS,
        f"got {risk_level!r}; expected one of {sorted(_VALID_RISK_LEVELS)}" if risk_level not in _VALID_RISK_LEVELS else "",
    ))

    one_line = str(posture.get("one_line", ""))
    results.append((
        "one_line > 30 chars",
        len(one_line) > 30,
        f"length {len(one_line)}" if len(one_line) <= 30 else "",
    ))

    one_line_lower = one_line.lower()
    detected = [w for w in _TECH_JARGON if w in one_line_lower]
    results.append((
        "one_line without technical jargon",
        not detected,
        f"detected: {detected}" if detected else "",
    ))

    # ── 8-9  business_risk quality ────────────────────────────────────────────
    br = es.get("business_risk", {})
    summary = str(br.get("summary", ""))
    results.append((
        "business_risk.summary > 80 chars",
        len(summary) > 80,
        f"length {len(summary)}" if len(summary) <= 80 else "",
    ))

    top_risks = br.get("top_risks", [])
    results.append((
        "top_risks not empty",
        len(top_risks) > 0,
        "top_risks is empty" if not top_risks else "",
    ))

    # ── 10-12  domain_highlights quality ─────────────────────────────────────
    domains = es.get("domain_highlights", [])
    results.append((
        "domain_highlights not empty",
        len(domains) > 0,
        "domain_highlights is empty" if not domains else "",
    ))

    # Criteria 11 and 12 always emitted; fail with explanation when domain is absent.
    if domains and isinstance(domains[0], dict):
        domain = domains[0]
        score = domain.get("score")
        results.append((
            "domain.score numeric",
            isinstance(score, (int, float)),
            f"got {type(score).__name__}" if not isinstance(score, (int, float)) else "",
        ))
        headline = str(domain.get("headline", ""))
        results.append((
            "domain.headline > 20 chars",
            len(headline) > 20,
            f"length {len(headline)}" if len(headline) <= 20 else "",
        ))
    else:
        results.append(("domain.score numeric", False, "no domain_highlights[0] to evaluate"))
        results.append(("domain.headline > 20 chars", False, "no domain_highlights[0] to evaluate"))

    # ── 13  recommendations quality ───────────────────────────────────────────
    recs = es.get("recommendations_30_60_90", {})
    days_30 = recs.get("days_30", [])

    # Criterion 13 always emitted; fail when days_30 is absent or entry is missing the key.
    if days_30 and isinstance(days_30[0], dict):
        rec = days_30[0]
        has_risk = bool(rec.get("risk_if_skipped"))
        results.append((
            "has risk_if_skipped",
            has_risk,
            "risk_if_skipped is empty or missing" if not has_risk else "",
        ))
    else:
        results.append(("has risk_if_skipped", False, "no days_30[0] to evaluate"))

    assert len(results) == _TOTAL_CRITERIA, (
        f"BUG: check_executive_summary must always return {_TOTAL_CRITERIA} entries, "
        f"got {len(results)}"
    )
    return results


# ── Formatters ─────────────────────────────────────────────────────────────────

def _print_results(analysis_type: str, results: list[tuple[str, bool, str]]) -> None:
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\nPrompt evaluation: {analysis_type}")
    print(f"Result: {passed}/{total} criteria passed\n")
    for criterion, ok, detail in results:
        mark = "✅" if ok else "❌"
        line = f"{mark} {criterion}"
        if not ok and detail:
            line += f" — {detail}"
        print(line)
    print()


def _save_results(
    analysis_type: str,
    results: list[tuple[str, bool, str]],
    source_file: str | None,
) -> Path:
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    payload = {
        "analysis_type": analysis_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_file": source_file,
        "passed": passed,
        "total": total,
        "criteria": [
            {"criterion": c, "passed": ok, "detail": d}
            for c, ok, d in results
        ],
    }
    out_dir = Path(__file__).resolve().parent.parent / "tmp"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = out_dir / f"prompt_eval_{analysis_type}_{ts}.json"
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Results saved to {out_path}")
    return out_path


# ── Dispatch ───────────────────────────────────────────────────────────────────

_EVALUATORS = {
    "executive_summary": check_executive_summary,
}


def evaluate(
    analysis_type: str,
    output: dict[str, Any],
    *,
    save: bool = False,
    source_file: str | None = None,
) -> list[tuple[str, bool, str]]:
    if analysis_type not in _EVALUATORS:
        supported = ", ".join(sorted(_EVALUATORS))
        raise ValueError(f"Unsupported analysis type {analysis_type!r}. Supported: {supported}")

    results = _EVALUATORS[analysis_type](output)
    _print_results(analysis_type, results)

    if save:
        _save_results(analysis_type, results, source_file)

    return results


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test_prompts.py",
        description=(
            "Evaluate an AI output JSON against measurable prompt quality criteria.\n"
            "No AI calls are made. No API key is required.\n\n"
            "Examples:\n"
            "  python scripts/test_prompts.py --type executive_summary --file output.json\n"
            "  python scripts/test_prompts.py --type executive_summary --file output.json --strict\n"
            "  python scripts/test_prompts.py --type executive_summary --file output.json --save"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--type",
        default="executive_summary",
        choices=list(_EVALUATORS),
        help="Analysis type to evaluate (default: executive_summary)",
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Path to a JSON file containing the AI output to evaluate",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save evaluation results to backend/tmp/prompt_eval_<type>_<ts>.json",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any criterion fails",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.file:
        parser.print_help()
        print(
            "\nError: --file is required. Provide a path to an AI output JSON.\n"
            "Example: --file /path/to/output.json\n"
            "\nTo generate a sample output for manual testing, run:\n"
            "  docker compose run --rm backend python scripts/seed_demo_data.py\n"
            "Then call the AI endpoint and save the response to a file."
        )
        return 2

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        return 2

    try:
        output = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {file_path}: {exc}", file=sys.stderr)
        return 2

    results = evaluate(
        args.type,
        output,
        save=args.save,
        source_file=str(file_path),
    )

    if args.strict:
        all_passed = all(ok for _, ok, _ in results)
        if not all_passed:
            failed = [c for c, ok, _ in results if not ok]
            print(f"--strict: {len(failed)} criterion/criteria failed: {failed}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

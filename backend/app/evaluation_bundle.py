"""Store and load full ML pipeline output without confusing it with the nested `feedback` summary dict."""

from __future__ import annotations

import copy
from typing import Any

from app.models import Result
from app.schemas import ResultListOut, ResultOut

# Wrapped shape avoids ever persisting only the inner human-readable `feedback` blob by mistake.
BUNDLE_KEY = "_evaluation_full_report_v1"


def compact_ml_result_for_storage(ml_result: dict[str, Any]) -> dict[str, Any]:
    """Drop large list fields; keep scores, OCR text, and breakdowns for the UI."""
    payload = copy.deepcopy(ml_result)
    nlp = payload.get("stages", {}).get("nlp_analysis")
    if isinstance(nlp, dict):
        for heavy in ("tokens", "pos_tags", "named_entities", "keywords"):
            nlp.pop(heavy, None)
    return payload


def bundle_evaluation(ml_result: dict[str, Any]) -> dict[str, Any]:
    if "stages" not in ml_result or "ocr_output" not in ml_result.get("stages", {}):
        raise ValueError("Incomplete ML pipeline result (missing stages.ocr_output).")
    compact = compact_ml_result_for_storage(ml_result)
    return {BUNDLE_KEY: compact}


def get_evaluation_report(stored: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the full pipeline dict if present, else None."""
    if not stored or not isinstance(stored, dict):
        return None
    if BUNDLE_KEY in stored:
        inner = stored[BUNDLE_KEY]
        return inner if isinstance(inner, dict) else None
    if "stages" in stored:
        return stored
    return None


def api_feedback_payload(stored: dict[str, Any] | None) -> dict[str, Any]:
    """Shape returned to the frontend as `feedback` on result endpoints."""
    report = get_evaluation_report(stored)
    if report:
        return report
    if isinstance(stored, dict) and stored.get("summary") is not None:
        return {
            "_evaluation_incomplete": True,
            "summary_feedback": stored,
            "message": "This result was saved before full reports were stored. Re-run evaluation to see metrics and extracted text.",
        }
    return {
        "_evaluation_incomplete": True,
        "summary_feedback": stored or {},
        "message": "No full evaluation payload on file. Re-run evaluation.",
    }


def extract_ocr_text_from_stored(stored: dict[str, Any] | None) -> str | None:
    report = get_evaluation_report(stored)
    if not report:
        return None
    text = report.get("stages", {}).get("ocr_output", {}).get("extracted_text")
    return text if isinstance(text, str) else None


def serialize_result_out(result: Result) -> ResultOut:
    return ResultOut(
        id=result.id,
        submission_id=result.submission_id,
        score=result.score,
        grade=result.grade,
        feedback=api_feedback_payload(result.feedback),
        created_by=result.created_by,
    )


def serialize_result_list_row(result: Result, assignment_title: str) -> ResultListOut:
    payload = api_feedback_payload(result.feedback)
    ocr = extract_ocr_text_from_stored(result.feedback)
    return ResultListOut(
        id=result.id,
        submission_id=result.submission_id,
        assignment_id=result.submission.assignment_id,
        assignment_title=assignment_title,
        student_id=result.submission.student_id,
        submitted_at=result.submission.submitted_at,
        has_submission_file=bool(result.submission.file_path),
        score=result.score,
        grade=result.grade,
        feedback=payload,
        ocr_extracted_text=ocr,
        created_by=result.created_by,
    )

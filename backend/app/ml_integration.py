import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from ml.pipeline import AssignmentEvaluationPipeline, EvaluationRequest


def _resolve_submission_path(file_path: str | None) -> str | None:
    if not file_path:
        return None

    path = Path(file_path).expanduser()
    if path.is_absolute() and path.exists():
        return str(path)

    backend_root = Path(__file__).resolve().parents[1]
    project_root = Path(__file__).resolve().parents[2]
    candidates = []

    # New format (relative path stored in DB, e.g. uploads/abc.jpg).
    if not path.is_absolute():
        candidates.extend([backend_root / path, project_root / path])

    # Legacy absolute paths that may no longer be valid; try basename fallback.
    candidates.extend(
        [
            backend_root / "uploads" / path.name,
            project_root / "backend" / "uploads" / path.name,
        ]
    )

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            return str(resolved)

    return str(path)


def evaluate_submission(
    student_id: int,
    assignment_id: int,
    submission_id: int,
    title: str,
    description: str,
    reference_answer: str,
    reference_keywords: list[str],
    reference_concepts: list[str],
    text: str | None,
    file_path: str | None,
) -> dict:
    pipeline = AssignmentEvaluationPipeline()

    request = EvaluationRequest(
        student_id=str(student_id),
        exam_id=str(assignment_id),
        question_id=str(submission_id),
        answer_script_path=_resolve_submission_path(file_path) or "typed_input.txt",
        question_text=f"{title}\n{description}",
        reference_answer=reference_answer or description,
        reference_keywords=reference_keywords or [],
        reference_concepts=reference_concepts or [],
        typed_text=text,
    )
    return pipeline.run(request)

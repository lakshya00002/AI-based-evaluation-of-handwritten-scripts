"""Cross-submission similarity for plagiarism-style flags."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.orm import PlagiarismFlag, Submission
from app.services import nlp_service


def max_similarity_to_cohort(
    db: Session,
    text: str,
    assignment_id: int,
    exclude_submission_id: int,
) -> Optional[tuple[int, float]]:
    """
    Compare embedding of `text` to other submissions on same assignment.

    Returns (other_submission_id, similarity) for max match, or None if no peers.
    """
    peers = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.id != exclude_submission_id,
            Submission.extracted_text.isnot(None),
        )
        .all()
    )
    if not peers:
        return None
    texts = [p.extracted_text or "" for p in peers]
    if not any(t.strip() for t in texts):
        return None
    emb_self = nlp_service.encode_texts([nlp_service.normalize_text(text)])
    emb_others = nlp_service.encode_texts([nlp_service.normalize_text(t) for t in texts])
    import numpy as np

    sims = np.dot(emb_others, emb_self.T).flatten()
    idx = int(np.argmax(sims))
    best = float(sims[idx])
    return peers[idx].id, max(0.0, min(1.0, best))


def record_flag(db: Session, sub_id: int, other_id: int, similarity: float, note: str | None = None) -> PlagiarismFlag:
    row = PlagiarismFlag(
        submission_id=sub_id,
        compared_submission_id=other_id,
        similarity=Decimal(str(round(similarity, 6))),
        note=note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

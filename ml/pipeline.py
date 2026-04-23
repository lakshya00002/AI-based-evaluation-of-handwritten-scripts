from __future__ import annotations

from dataclasses import asdict, dataclass

from ml.config import PipelineConfig
from ml.data_acquisition import SubmissionMetadata, acquire_input
from ml.deep_analysis import run_deep_analysis
from ml.error_metrics import compute_ocr_error_metrics
from ml.feedback_generator import generate_feedback
from ml.nlp_analysis import run_nlp_analysis
from ml.ocr_module import extract_text
from ml.scoring_engine import compute_final_score


@dataclass
class EvaluationRequest:
    student_id: str
    exam_id: str
    question_id: str
    answer_script_path: str
    question_text: str
    reference_answer: str
    reference_keywords: list[str]
    reference_concepts: list[str]
    typed_text: str | None = None
    ocr_ground_truth_text: str | None = None


class AssignmentEvaluationPipeline:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def run(self, request: EvaluationRequest) -> dict:
        ocr_engine = "none"
        # 1) Data acquisition
        submission = SubmissionMetadata(
            student_id=request.student_id,
            exam_id=request.exam_id,
            question_id=request.question_id,
            answer_script_path=request.answer_script_path,
            typed_text=request.typed_text,
        )
        acquisition = acquire_input(submission, min_dpi=self.config.min_dpi)

        # 2) Preprocessing + 3) OCR
        if acquisition.input_mode == "typed" and request.typed_text:
            extracted_text = request.typed_text.strip()
            ocr_notes = ["OCR bypassed for typed text."]
        else:
            path = acquisition.validated_path
            if path is None:
                raise ValueError("No valid path available for OCR stage.")
            ocr_output = extract_text(path)
            extracted_text = ocr_output.extracted_text
            ocr_notes = list(ocr_output.notes)
            ocr_engine = ocr_output.engine_used
            if request.typed_text and request.typed_text.strip():
                sup = request.typed_text.strip()
                extracted_text = f"{extracted_text}\n\n{sup}" if extracted_text.strip() else sup
                ocr_notes.append("Appended typed supplement after OCR transcript.")

        # 4) NLP analysis
        nlp = run_nlp_analysis(
            student_text=extracted_text,
            reference_answer=request.reference_answer,
            reference_keywords=request.reference_keywords,
            question_text=request.question_text,
        )

        # 5) OCR error analysis (requires ground-truth transcript)
        ocr_error = compute_ocr_error_metrics(
            extracted_text=extracted_text,
            ground_truth_text=request.ocr_ground_truth_text,
        )

        # 6) Deep learning analysis
        deep = run_deep_analysis(
            student_text=extracted_text,
            reference_answer=request.reference_answer,
            reference_concepts=request.reference_concepts,
        )

        # 7) Adaptive scoring engine with weighted metric fusion
        score = compute_final_score(
            keyword_coverage_score=nlp.keyword_score,
            bleu_score=nlp.bleu_score,
            rouge_score=max(nlp.rouge_1_recall, nlp.rouge_l_recall),
            semantic_score=nlp.semantic_similarity_score,
            relevance_score=nlp.relevance_completeness_score,
            concept_coverage=deep.concept_coverage_score,
            structure_score=nlp.structure_score,
            length_normalization_score=nlp.length_normalization_score,
            config=self.config,
        )

        # 8) Feedback generation
        feedback = generate_feedback(
            student_keywords=nlp.keywords,
            reference_keywords=request.reference_keywords,
            missing_concepts=deep.missing_concepts,
            keyword_score=nlp.keyword_score,
            semantic_score=nlp.semantic_similarity_score,
            grammar_score=nlp.grammar_score,
            coherence_score=deep.coherence_score,
            relevance_score=nlp.relevance_completeness_score,
            final_score=score.final_score_0_1,
        )

        return {
            "metadata": {
                "student_id": request.student_id,
                "exam_id": request.exam_id,
                "question_id": request.question_id,
                "answer_script_path": request.answer_script_path,
            },
            "stages": {
                "data_acquisition": {
                    "input_mode": acquisition.input_mode,
                    "dpi_ok": acquisition.dpi_ok,
                    "notes": acquisition.notes,
                },
                "ocr_output": {
                    "engine_used": "none" if acquisition.input_mode == "typed" and request.typed_text else ocr_engine,
                    "extracted_text": extracted_text,
                    "extracted_text_present": bool(extracted_text.strip()),
                    "notes": ocr_notes,
                },
                "ocr_error_analysis": asdict(ocr_error),
                "nlp_analysis": asdict(nlp),
                "deep_analysis": asdict(deep),
                "adaptive_scoring": {
                    "weights": asdict(self.config.scoring_weights.normalized()),
                    "weighted_contributions": score.weighted_breakdown,
                    "final_score_formula": "sum(weight_i * metric_i)",
                },
            },
            "final_evaluation": asdict(score),
            "feedback": feedback,
        }


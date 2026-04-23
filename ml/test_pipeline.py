from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.config import PipelineConfig, ScoringWeights
from ml.pipeline import AssignmentEvaluationPipeline, EvaluationRequest


DEFAULT_QUESTION = "Explain backpropagation in neural networks and why it is important for training."
DEFAULT_REFERENCE_ANSWER = (
    "Backpropagation computes gradients of the loss with respect to model weights using the chain rule. "
    "It propagates error from output to hidden layers, enabling gradient descent to update parameters and reduce loss."
)
DEFAULT_REFERENCE_KEYWORDS = [
    "backpropagation",
    "chain rule",
    "gradient",
    "loss function",
    "weights",
    "gradient descent",
]
DEFAULT_REFERENCE_CONCEPTS = [
    "error propagation through layers",
    "derivative of loss with respect to weights",
    "parameter updates with gradient descent",
]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run assignment evaluation pipeline end-to-end.")
    parser.add_argument("--input", required=True, help="Path to input file (.jpg/.png/.pdf/.txt).")
    parser.add_argument("--student-id", default="S001")
    parser.add_argument("--exam-id", default="EXAM-01")
    parser.add_argument("--question-id", default="Q1")
    parser.add_argument("--typed-text", default=None, help="Direct typed answer text. Overrides OCR file content.")
    parser.add_argument(
        "--ocr-ground-truth",
        default=None,
        help="Ground-truth transcript for CER/WER against OCR extracted text.",
    )
    parser.add_argument("--max-marks", type=int, default=10)
    return parser


def run_pipeline_from_args(args: argparse.Namespace) -> dict:
    config = PipelineConfig(
        max_marks=args.max_marks,
        min_dpi=300,
        scoring_weights=ScoringWeights(
            w1_keyword_coverage=0.12,
            w2_bleu_surface=0.10,
            w3_rouge_recall=0.12,
            w4_semantic_correctness=0.24,
            w5_concept_coverage=0.18,
            w6_structure_quality=0.12,
            w7_relevance=0.06,
            w8_length_normalization=0.06,
        ),
    )
    pipeline = AssignmentEvaluationPipeline(config=config)
    request = EvaluationRequest(
        student_id=args.student_id,
        exam_id=args.exam_id,
        question_id=args.question_id,
        answer_script_path=str(Path(args.input).resolve()),
        typed_text=args.typed_text,
        ocr_ground_truth_text=args.ocr_ground_truth,
        question_text=DEFAULT_QUESTION,
        reference_answer=DEFAULT_REFERENCE_ANSWER,
        reference_keywords=DEFAULT_REFERENCE_KEYWORDS,
        reference_concepts=DEFAULT_REFERENCE_CONCEPTS,
    )
    return pipeline.run(request)


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    result = run_pipeline_from_args(args)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()


"""Read-only evidence normalization."""
from qwen3_coder_next.evaluation.schemas import EvidenceBundle, EvaluationRunRequest

class EvidenceCollector:
    def collect(self, request: EvaluationRunRequest) -> EvidenceBundle:
        if not isinstance(request, EvaluationRunRequest): raise ValueError("request must be an EvaluationRunRequest.")
        tests = tuple(item.strip() for item in request.test_artifacts if item.strip())
        review = tuple(item.strip() for item in request.review_notes if item.strip())
        missing = tuple(sorted({name for name, value in (("test_artifacts", tests), ("review_notes", review), ("patch_summary", request.patch_summary.strip())) if not value}))
        return EvidenceBundle(tests, review, request.patch_summary.strip(), request.memory_refs, missing)


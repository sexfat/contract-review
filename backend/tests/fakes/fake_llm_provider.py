from __future__ import annotations

from collections.abc import Callable

from app.domain.schemas.llm_classification import LLMClassificationRequest, LLMClassificationResult

Scripted = LLMClassificationResult | Exception | Callable[[LLMClassificationRequest], LLMClassificationResult]


class FakeLLMProvider:
    """Test double for LLMProvider. `script` maps clause_id -> a list of
    results/exceptions/callables consumed in order across successive calls
    (one entry per attempt, including retries). A clause_id missing from
    `script` falls back to `default_result_factory` for every call."""

    def __init__(
        self,
        script: dict[str, list[Scripted]] | None = None,
        default_result_factory: Callable[[LLMClassificationRequest], LLMClassificationResult] | None = None,
        model_id: str = "fake-model",
    ) -> None:
        self.model_id = model_id
        self._script = {k: list(v) for k, v in (script or {}).items()}
        self._default_result_factory = default_result_factory
        self.calls: list[LLMClassificationRequest] = []

    def classify_clause(self, request: LLMClassificationRequest) -> LLMClassificationResult:
        self.calls.append(request)
        queue = self._script.get(request.clause_id)

        if queue:
            step = queue.pop(0)
        elif self._default_result_factory is not None:
            step = self._default_result_factory(request)
        else:
            raise AssertionError(f"FakeLLMProvider: no scripted step for {request.clause_id}")

        if isinstance(step, Exception):
            raise step
        if callable(step) and not isinstance(step, LLMClassificationResult):
            return step(request)
        return step

from __future__ import annotations

from collections.abc import Callable

from app.domain.schemas.llm_risk_assessment import RiskAssessmentRequest, RiskAssessmentResult

Scripted = RiskAssessmentResult | Exception | Callable[[RiskAssessmentRequest], RiskAssessmentResult]


class FakeRiskAssessmentProvider:
    """Test double for RiskAssessmentProvider, mirroring FakeLLMProvider
    (002). `script` is keyed by (clause_id, rule_id) — one list of
    results/exceptions/callables consumed in order across successive calls
    for that pair (one entry per attempt, including retries)."""

    def __init__(
        self,
        script: dict[tuple[str, str], list[Scripted]] | None = None,
        default_result_factory: Callable[[RiskAssessmentRequest], RiskAssessmentResult] | None = None,
        model_id: str = "fake-model",
    ) -> None:
        self.model_id = model_id
        self._script = {k: list(v) for k, v in (script or {}).items()}
        self._default_result_factory = default_result_factory
        self.calls: list[RiskAssessmentRequest] = []

    def assess_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResult:
        self.calls.append(request)
        key = (request.clause_id, request.rule_id)
        queue = self._script.get(key)

        if queue:
            step = queue.pop(0)
        elif self._default_result_factory is not None:
            step = self._default_result_factory(request)
        else:
            raise AssertionError(f"FakeRiskAssessmentProvider: no scripted step for {key}")

        if isinstance(step, Exception):
            raise step
        if callable(step) and not isinstance(step, RiskAssessmentResult):
            return step(request)
        return step

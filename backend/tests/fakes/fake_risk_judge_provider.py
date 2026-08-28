from __future__ import annotations

from collections.abc import Callable

from app.domain.schemas.judge import JudgeRequest, JudgeResult

Scripted = JudgeResult | Exception | Callable[[JudgeRequest], JudgeResult]

_ALWAYS_PASS = JudgeResult(passed=True, reason="測試預設：一律通過")


class FakeRiskJudgeProvider:
    """Test double for RiskJudgeProvider, mirroring FakeRiskAssessmentProvider.
    Defaults to always-passing so tests unrelated to judge gate don't need to
    script it explicitly."""

    def __init__(
        self,
        script: dict[tuple[str, str], list[Scripted]] | None = None,
        default_result_factory: Callable[[JudgeRequest], JudgeResult] | None = None,
        model_id: str = "fake-judge-model",
    ) -> None:
        self.model_id = model_id
        self._script = {k: list(v) for k, v in (script or {}).items()}
        self._default_result_factory = default_result_factory
        self.calls: list[JudgeRequest] = []

    def judge(self, request: JudgeRequest) -> JudgeResult:
        self.calls.append(request)
        # No natural (clause_id, rule_id) key on JudgeRequest itself — callers
        # that need per-pair scripting key by clause_original_text instead.
        key = request.clause_original_text
        queue = self._script.get(key)

        if queue:
            step = queue.pop(0)
        elif self._default_result_factory is not None:
            step = self._default_result_factory(request)
        else:
            step = _ALWAYS_PASS

        if isinstance(step, Exception):
            raise step
        if callable(step) and not isinstance(step, JudgeResult):
            return step(request)
        return step

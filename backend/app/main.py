from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes_classification import router as classification_router
from app.api.routes_documents import router as documents_router
from app.api.routes_review import router as review_router
from app.domain.errors import DomainError

logger = logging.getLogger("contract_review")

_ERROR_STATUS_CODES: dict[str, int] = {
    "UNSUPPORTED_FILE_TYPE": 400,
    "FILE_TOO_LARGE": 400,
    "INVALID_DOCX": 400,
    "TRACKED_CHANGES_NOT_SUPPORTED": 400,
    "DOCUMENT_NOT_READY": 409,
    "DOCUMENT_NOT_FOUND": 404,
    "LLM_OUTPUT_INVALID": 400,
    "LLM_PROVIDER_UNAVAILABLE": 502,
}

app = FastAPI(title="合約審閱助手 API")
app.include_router(documents_router)
app.include_router(classification_router)
app.include_router(review_router)


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    # Log only document_id (from the path) and the error code/stack — never
    # contract text (DEVELOPMENT_SPEC.md #12, spec.md "Failure handling").
    document_id = request.path_params.get("document_id")
    logger.warning(
        "document_error",
        extra={"document_id": document_id, "error_code": exc.error_code},
        exc_info=exc,
    )
    status_code = _ERROR_STATUS_CODES.get(exc.error_code, 400)
    return JSONResponse(
        status_code=status_code,
        content={"error_code": exc.error_code, "message": exc.user_message},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

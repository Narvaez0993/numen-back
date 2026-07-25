from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from structlog import get_logger

from src.shared.domain.errors import DomainError

_logger = get_logger(__name__)


def _validation_response(details: object) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "common.validation",
            "message": "Invalid request payload",
            "details": details,
        },
    )


async def _domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "message": exc.message,
        },
    )


async def _pydantic_validation_handler(
    _request: Request, exc: PydanticValidationError
) -> JSONResponse:
    return _validation_response(exc.errors(include_url=False))


async def _request_validation_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """FastAPI raises its own error for a malformed body, which does not inherit
    from pydantic's — without this handler those 422s would answer `{detail: ...}`
    and break the `{code, message}` contract every client maps against."""
    return _validation_response(exc.errors())


async def _unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
    _logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "code": "common.internal_error",
            "message": "An unexpected error occurred",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire all domain-aware exception handlers on the FastAPI app."""
    app.add_exception_handler(DomainError, _domain_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _request_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(PydanticValidationError, _pydantic_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_handler)

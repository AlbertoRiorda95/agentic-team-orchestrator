"""RFC 9457 problem details for every error response."""

import logging
from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic.json_schema import SkipJsonSchema
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(__name__)


class FieldError(BaseModel):
    field: str
    message: str


class Problem(BaseModel):
    """RFC 9457 problem details. Optional members are omitted, never null."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | SkipJsonSchema[None] = None
    errors: list[FieldError] | SkipJsonSchema[None] = None


class ProblemResponse(JSONResponse):
    media_type = PROBLEM_MEDIA_TYPE


def problem_response(
    status: int,
    *,
    detail: str | None = None,
    errors: list[FieldError] | None = None,
    headers: Mapping[str, str] | None = None,
) -> ProblemResponse:
    problem = Problem(title=HTTPStatus(status).phrase, status=status, detail=detail, errors=errors)
    return ProblemResponse(
        problem.model_dump(mode="json", exclude_none=True), status_code=status, headers=headers
    )


async def handle_http_exception(request: Request, exc: Exception) -> ProblemResponse:
    if not isinstance(exc, StarletteHTTPException):
        return await handle_unexpected_error(request, exc)
    title = HTTPStatus(exc.status_code).phrase
    # Starlette's default detail repeats the title: keep only a meaningful one
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != title else None
    return problem_response(exc.status_code, detail=detail, headers=exc.headers)


async def handle_validation_error(request: Request, exc: Exception) -> ProblemResponse:
    if not isinstance(exc, RequestValidationError):
        return await handle_unexpected_error(request, exc)
    errors = [
        FieldError(field=".".join(str(part) for part in error["loc"]), message=error["msg"])
        for error in exc.errors()
    ]
    return problem_response(
        HTTPStatus.UNPROCESSABLE_CONTENT, detail="The request is not valid.", errors=errors
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> ProblemResponse:
    # %r: the path comes from the client, keep control characters out of the log
    logger.exception("unhandled error on %s %r", request.method, request.url.path, exc_info=exc)
    return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR)


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)

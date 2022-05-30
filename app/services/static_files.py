"""Static smartapp files."""
import os
import typing

from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.responses import FileResponse, Response
from starlette.staticfiles import NotModifiedResponse
from starlette.types import Scope

PathLike = typing.Union[str, "os.PathLike[str]"]


class StaticFilesCustomHeaders(StaticFiles):
    def __init__(
        self,
        *,
        directory: PathLike = None,
        packages: typing.List[str] = None,
        html: bool = False,
        check_dir: bool = True,
        headers: dict = None,
    ) -> None:
        """Save custom headers."""
        super().__init__(
            directory=directory, packages=packages, html=html, check_dir=check_dir
        )
        self.headers = headers

    def file_response(
        self,
        full_path: PathLike,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        """Patch file_response from starlette.StaticFiles to add headers."""
        method = scope["method"]
        request_headers = Headers(scope=scope)

        response = FileResponse(
            full_path,
            status_code=status_code,
            stat_result=stat_result,
            method=method,
            headers=self.headers,
        )
        if self.is_not_modified(response.headers, request_headers):
            return NotModifiedResponse(response.headers)

        return response

"""OpenAPI utils."""
from typing import Any, Dict, Sequence, Tuple

from fastapi.encoders import jsonable_encoder
from fastapi.openapi.models import OpenAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security.base import SecurityBase
from pybotx_smartapp_rpc import RPCRouter
from pybotx_smartapp_rpc.openapi_utils import (
    get_rpc_flat_models_from_routes,
    get_rpc_model_definitions,
    get_rpc_openapi_path,
)
from pydantic.schema import get_model_name_map
from starlette.routing import BaseRoute

from app.services.execute_rpc import security


def get_openapi_security_definitions(
    security_component: SecurityBase,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    security_definition = jsonable_encoder(
        security_component.model,
        by_alias=True,
        exclude_none=True,
    )
    security_name = security_component.scheme_name
    security_definitions = {security_name: security_definition}
    operation_security = {security_name: []}  # type: ignore
    return security_definitions, operation_security


def custom_openapi(
    *,
    title: str,
    version: str,
    fastapi_routes: Sequence[BaseRoute],
    rpc_router: RPCRouter,
    **kwargs: Any,
) -> Dict[str, Any]:
    openapi_dict = get_openapi(
        title=title,
        version=version,
        routes=fastapi_routes,
        **kwargs,
    )

    paths: Dict[str, Dict[str, Any]] = {}

    flat_rpc_models = get_rpc_flat_models_from_routes(rpc_router)
    rpc_model_name_map = get_model_name_map(flat_rpc_models)
    rpc_definitions = get_rpc_model_definitions(
        flat_models=flat_rpc_models, model_name_map=rpc_model_name_map
    )
    security_definitions, operation_security = get_openapi_security_definitions(
        security_component=security
    )

    for method_name in rpc_router.rpc_methods.keys():
        if not rpc_router.rpc_methods[method_name].include_in_schema:
            continue

        path = get_rpc_openapi_path(  # type: ignore
            method_name=method_name,
            route=rpc_router.rpc_methods[method_name],
            model_name_map=rpc_model_name_map,
            security_scheme=operation_security,
        )
        if path:
            paths.setdefault(f"/{method_name}", {}).update(path)

    if rpc_definitions:
        openapi_dict.setdefault("components", {}).setdefault("schemas", {}).update(
            {k: rpc_definitions[k] for k in sorted(rpc_definitions)}
        )

    openapi_dict.setdefault("components", {}).setdefault("securitySchemes", {}).update(
        security_definitions
    )
    openapi_dict.setdefault("paths", {}).update(paths)

    return jsonable_encoder(OpenAPI(**openapi_dict), by_alias=True, exclude_none=True)

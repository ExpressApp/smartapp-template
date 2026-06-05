"""OpenAPI utils."""

from collections.abc import Sequence
from enum import Enum
from typing import Any

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
from pydantic import BaseModel
from starlette.routing import BaseRoute

from app.services.execute_rpc import security


def get_openapi_security_definitions(
    security_component: SecurityBase,
) -> tuple[dict[str, Any], dict[str, Any]]:
    security_definition = jsonable_encoder(
        security_component.model,
        by_alias=True,
        exclude_none=True,
    )
    security_name = security_component.scheme_name
    security_definitions = {security_name: security_definition}
    operation_security = {security_name: []}  # type: ignore
    return security_definitions, operation_security


def get_model_name_map(
    flat_models: set[type[BaseModel] | type[Enum]],
) -> dict[type[BaseModel] | type[Enum], str]:
    """Build stable schema names for RPC models under Pydantic v2."""
    name_counts: dict[str, int] = {}
    model_name_map: dict[type[BaseModel] | type[Enum], str] = {}

    for model in sorted(
        flat_models, key=lambda item: f"{item.__module__}.{item.__name__}"
    ):
        model_name = model.__name__
        name_counts[model_name] = name_counts.get(model_name, 0) + 1

        if name_counts[model_name] == 1:
            model_name_map[model] = model_name
            continue

        model_name_map[model] = f"{model.__module__.replace('.', '_')}__{model_name}"

    return model_name_map


def custom_openapi(
    *,
    title: str,
    version: str,
    fastapi_routes: Sequence[BaseRoute],
    rpc_router: RPCRouter,
    **kwargs: Any,
) -> dict[str, Any]:
    openapi_dict = get_openapi(
        title=title,
        version=version,
        routes=fastapi_routes,
        **kwargs,
    )

    paths: dict[str, dict[str, Any]] = {}

    flat_rpc_models = get_rpc_flat_models_from_routes(rpc_router)
    rpc_model_name_map = get_model_name_map(flat_rpc_models)
    rpc_definitions = get_rpc_model_definitions(
        flat_models=flat_rpc_models, model_name_map=rpc_model_name_map
    )
    security_definitions, operation_security = get_openapi_security_definitions(
        security_component=security
    )

    for method_name in rpc_router.rpc_methods:
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

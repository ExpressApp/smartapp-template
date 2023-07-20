"""OpenAPI utils."""
from typing import Any, Dict, List, Optional, Sequence, Union

from fastapi import routing
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.models import OpenAPI
from fastapi.openapi.utils import get_flat_models_from_routes, get_openapi_path
from fastapi.utils import get_model_definitions
from pybotx_smartapp_rpc import RPCRouter
from pybotx_smartapp_rpc.openapi_utils import (
    get_rpc_flat_models_from_routes,
    get_rpc_openapi_path,
)
from pydantic.schema import get_model_name_map
from starlette.routing import BaseRoute


def custom_openapi(
    *,
    title: str,
    version: str,
    openapi_version: str = "3.0.2",
    description: Optional[str] = None,
    fastapi_routes: Sequence[BaseRoute],
    rpc_router: RPCRouter,
    tags: Optional[List[Dict[str, Any]]] = None,
    servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
    terms_of_service: Optional[str] = None,
    contact: Optional[Dict[str, Union[str, Any]]] = None,
    license_info: Optional[Dict[str, Union[str, Any]]] = None,
) -> Dict[str, Any]:
    info: Dict[str, Any] = {"title": title, "version": version}
    if description:
        info["description"] = description
    if terms_of_service:
        info["termsOfService"] = terms_of_service
    if contact:
        info["contact"] = contact
    if license_info:
        info["license"] = license_info
    output: Dict[str, Any] = {"openapi": openapi_version, "info": info}
    if servers:
        output["servers"] = servers
    components: Dict[str, Dict[str, Any]] = {}
    paths: Dict[str, Dict[str, Any]] = {}
    # FastAPI
    flat_fastapi_models = get_flat_models_from_routes(fastapi_routes)
    fastapi_model_name_map = get_model_name_map(flat_fastapi_models)
    fast_api_definitions = get_model_definitions(
        flat_models=flat_fastapi_models, model_name_map=fastapi_model_name_map
    )

    # pybotx RPC
    flat_rpc_models = get_rpc_flat_models_from_routes(rpc_router)
    rpc_model_name_map = get_model_name_map(flat_rpc_models)
    rpc_definitions = get_model_definitions(
        flat_models=flat_rpc_models, model_name_map=rpc_model_name_map
    )

    for route in fastapi_routes:
        if isinstance(route, routing.APIRoute):
            result = get_openapi_path(
                route=route, model_name_map=fastapi_model_name_map
            )
            if result:
                path, security_schemes, path_definitions = result
                if path:
                    paths.setdefault(route.path_format, {}).update(path)
                if security_schemes:
                    components.setdefault("securitySchemes", {}).update(
                        security_schemes
                    )
                if path_definitions:
                    fast_api_definitions.update(path_definitions)

    for method_name in rpc_router.rpc_methods.keys():
        if not rpc_router.rpc_methods[method_name].include_in_schema:
            continue

        result = get_rpc_openapi_path(  # type: ignore
            method_name=method_name,
            route=rpc_router.rpc_methods[method_name],
            model_name_map=rpc_model_name_map,
        )
        if result:
            path, path_definitions = result  # type: ignore
            if path:
                paths.setdefault(method_name, {}).update(path)

            if path_definitions:
                rpc_definitions.update(path_definitions)

    if fast_api_definitions:
        components["schemas"] = {
            k: fast_api_definitions[k] for k in sorted(fast_api_definitions)
        }
    if rpc_definitions:
        components.setdefault("schemas", {}).update(
            {k: rpc_definitions[k] for k in sorted(rpc_definitions)}
        )
    if components:
        output["components"] = components
    output["paths"] = paths
    if tags:
        output["tags"] = tags

    return jsonable_encoder(OpenAPI(**output), by_alias=True, exclude_none=True)

"""Configuration for smartapp instance."""
from pybotx_smartapp_rpc import SmartAppRPC
from pybotx_smartapp_smart_logger import smartapp_exception_handler

from app.smartapp.rpc_methods import common

smartapp = SmartAppRPC(
    routers=[common.rpc],
    exception_handlers={Exception: smartapp_exception_handler},
)

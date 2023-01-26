"""Configuration for smartapp instance."""
from pybotx_smartapp_rpc import SmartAppRPC

from app.smartapp.middlewares.smartlogger import smart_logger_middleware
from app.smartapp.rpc_methods import common

smartapp = SmartAppRPC(
    routers=[common.rpc],
    middlewares=[smart_logger_middleware],
)

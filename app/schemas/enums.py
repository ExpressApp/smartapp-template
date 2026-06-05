"""Module for enums."""

from enum import Enum


class StrEnum(str, Enum):
    """Base enum."""


class HealthCheckStatuses(StrEnum):
    OK = "ok"
    ERROR = "error"

"""Enums for rocket states and job statuses."""
from enum import Enum


class RocketState(str, Enum):
    """Rocket state enumeration."""
    PREPARING = "Preparing"
    READY = "Ready"
    IN_FLIGHT = "InFlight"
    LANDED = "Landed"
    RUD = "RUD"  # Rapid Unscheduled Destruction


class JobStatus(str, Enum):
    """Job status enumeration."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"



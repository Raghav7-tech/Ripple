"""Ripple deterministic dependency-intelligence core."""

from .advisory import Advisory, compose_advisory, validate_generated_advisory
from .engine import CascadeEngine
from .forecast import ExplainableBaselinePredictor, ShortageFeatures, ShortageForecast
from .models import DependencyGraph, ImpactResult, Observation, ResourceType, Severity, ValidationError

__all__ = [
    "Advisory",
    "CascadeEngine",
    "DependencyGraph",
    "ImpactResult",
    "Observation",
    "ResourceType",
    "ExplainableBaselinePredictor",
    "ShortageFeatures",
    "ShortageForecast",
    "Severity",
    "ValidationError",
    "compose_advisory",
    "validate_generated_advisory",
]

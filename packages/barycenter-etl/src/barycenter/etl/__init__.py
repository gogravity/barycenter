"""Barycenter Tool Onboarding Framework + ConnectWise Manage adapter.

Public surface — single canonical import path (mirrors barycenter.audit
convention). Adapter authors should import from ``barycenter.etl`` rather
than reaching into submodules.
"""
from barycenter.etl.primitives import (
    PRIMITIVE_REGISTRY,
    PrimitiveResult,
    VALID_FIELD_CLASSES,
    drop,
    hash_,
    pseudonymize,
    aggregate,
    bucket,
    score,
    keyword_flags,
    as_is,
)
from barycenter.etl.framework.recipe import ETLRecipe
from barycenter.etl.framework.exceptions import (
    ETLError,
    CUIBoundaryViolation,
    SchemaDriftError,
    RateLimitExhausted,
    PaginationTruncated,
)
from barycenter.etl.framework.pseudonymizer import Pseudonymizer
from barycenter.etl.framework.canary import CanaryScanner
from barycenter.etl.framework.cui_gate import CUIGate
from barycenter.etl.framework.shape_builder import ShapeBuilder
from barycenter.etl.framework.adapter_base import Category

__all__ = [
    # primitives
    "PRIMITIVE_REGISTRY",
    "PrimitiveResult",
    "VALID_FIELD_CLASSES",
    "drop",
    "hash_",
    "pseudonymize",
    "aggregate",
    "bucket",
    "score",
    "keyword_flags",
    "as_is",
    # framework
    "ETLRecipe",
    "Pseudonymizer",
    "CanaryScanner",
    "CUIGate",
    "ShapeBuilder",
    "Category",
    # exceptions
    "ETLError",
    "CUIBoundaryViolation",
    "SchemaDriftError",
    "RateLimitExhausted",
    "PaginationTruncated",
]

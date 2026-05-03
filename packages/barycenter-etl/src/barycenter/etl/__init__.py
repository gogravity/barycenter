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
    # exceptions
    "ETLError",
    "CUIBoundaryViolation",
    "SchemaDriftError",
    "RateLimitExhausted",
    "PaginationTruncated",
]

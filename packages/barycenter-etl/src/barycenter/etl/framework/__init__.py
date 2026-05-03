"""ETL framework: ETLRecipe, exception hierarchy, Pseudonymizer, gate layer."""
from barycenter.etl.framework.exceptions import (
    ETLError,
    CUIBoundaryViolation,
    SchemaDriftError,
    RateLimitExhausted,
    PaginationTruncated,
)
from barycenter.etl.framework.pseudonymizer import Pseudonymizer
from barycenter.etl.framework.recipe import ETLRecipe, iter_all_recipes
from barycenter.etl.framework.canary import CanaryScanner
from barycenter.etl.framework.cui_gate import CUIGate
from barycenter.etl.framework.shape_builder import ShapeBuilder
from barycenter.etl.framework.adapter_base import Category

__all__ = [
    "ETLRecipe",
    "Pseudonymizer",
    "CanaryScanner",
    "CUIGate",
    "ShapeBuilder",
    "Category",
    "ETLError",
    "CUIBoundaryViolation",
    "SchemaDriftError",
    "RateLimitExhausted",
    "PaginationTruncated",
    "iter_all_recipes",
]

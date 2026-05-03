"""ETL framework: ETLRecipe, exception hierarchy, Pseudonymizer."""
from barycenter.etl.framework.exceptions import (
    ETLError,
    CUIBoundaryViolation,
    SchemaDriftError,
    RateLimitExhausted,
    PaginationTruncated,
)
from barycenter.etl.framework.pseudonymizer import Pseudonymizer
from barycenter.etl.framework.recipe import ETLRecipe, iter_all_recipes

__all__ = [
    "ETLRecipe",
    "Pseudonymizer",
    "ETLError",
    "CUIBoundaryViolation",
    "SchemaDriftError",
    "RateLimitExhausted",
    "PaginationTruncated",
    "iter_all_recipes",
]

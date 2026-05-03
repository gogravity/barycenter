"""Eight transformation primitives (TOOL-02).

Adapters compose ETL recipes only from these functions. The PRIMITIVE_REGISTRY
constant is the single source of truth that ETLRecipe.validate_no_bypass and
the test_recipe_no_bypass CI gate reference.
"""
from barycenter.etl.primitives._result import PrimitiveResult, VALID_FIELD_CLASSES
from barycenter.etl.primitives.drop import drop
from barycenter.etl.primitives.hash import hash_
from barycenter.etl.primitives.pseudonymize import pseudonymize
from barycenter.etl.primitives.aggregate import aggregate
from barycenter.etl.primitives.bucket import bucket
from barycenter.etl.primitives.score import score
from barycenter.etl.primitives.keyword_flags import keyword_flags
from barycenter.etl.primitives.as_is import as_is
from barycenter.etl.primitives.any_keyword import any_keyword

PRIMITIVE_REGISTRY = {
    "drop": drop,
    "hash": hash_,
    "pseudonymize": pseudonymize,
    "aggregate": aggregate,
    "bucket": bucket,
    "score": score,
    "keyword_flags": keyword_flags,
    "as_is": as_is,
    "any_keyword": any_keyword,
}

__all__ = [
    "PrimitiveResult",
    "VALID_FIELD_CLASSES",
    "PRIMITIVE_REGISTRY",
    "drop",
    "hash_",
    "pseudonymize",
    "aggregate",
    "bucket",
    "score",
    "keyword_flags",
    "as_is",
    "any_keyword",
]

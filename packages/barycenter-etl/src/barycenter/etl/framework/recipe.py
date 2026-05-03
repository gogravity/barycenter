"""ETLRecipe: declarative composition of primitives that yields parameterized SQL.

A recipe is a mapping of target column -> (primitive_name, kwargs). At
construction the field_validator walks the derivations and asserts every
primitive_name is a member of barycenter.etl.primitives.PRIMITIVE_REGISTRY
(TOOL-02 no-bypass invariant, threat T-02-10). The CI gate
test_recipe_no_bypass.py walks every recipe per build and re-checks this
invariant against the same registry constant.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ETLRecipe(BaseModel):
    """Declarative recipe; compiles to ``(sql_template, params)``."""

    model_config = ConfigDict(extra="forbid", frozen=False, arbitrary_types_allowed=True)

    target_table: str
    # column_name -> (primitive_name, kwargs_dict)
    derivations: dict[str, tuple[str, dict[str, Any]]]

    @field_validator("derivations")
    @classmethod
    def validate_no_bypass(cls, v: dict) -> dict:
        # Local import to dodge import-order issues — primitives module is the
        # source of truth and importing it at module load can race with the
        # framework barrel during package import.
        from barycenter.etl.primitives import PRIMITIVE_REGISTRY

        for col, deriv in v.items():
            if not (isinstance(deriv, tuple) and len(deriv) == 2):
                raise ValueError(
                    f"derivation for {col!r} must be (primitive_name, kwargs); "
                    f"got {deriv!r}"
                )
            primitive_name, kwargs = deriv
            if primitive_name not in PRIMITIVE_REGISTRY:
                raise ValueError(
                    f"recipe column {col!r} bypasses primitive layer: "
                    f"{primitive_name!r} not in PRIMITIVE_REGISTRY"
                )
            if not isinstance(kwargs, dict):
                raise ValueError(
                    f"derivation kwargs for {col!r} must be a dict, got {kwargs!r}"
                )
        return v

    def compile(
        self,
        record: dict,
        *,
        kv_client=None,
        tenant_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Apply each primitive against ``record`` and build an INSERT projection.

        Returns ``(sql_template, params_dict)``. Primitives never execute SQL;
        the caller binds params and runs the statement under its own transaction.
        """
        from barycenter.etl.primitives import PRIMITIVE_REGISTRY

        cols: list[str] = []
        exprs: list[str] = []
        params: dict[str, Any] = {}

        for col, (primitive_name, kwargs) in self.derivations.items():
            fn = PRIMITIVE_REGISTRY[primitive_name]
            source_field = kwargs.get("field")
            value = _resolve_field(record, source_field) if source_field else None

            if primitive_name == "drop":
                res = fn(source_field or col)
            elif primitive_name == "hash":
                res = fn(col, value if value is not None else "")
            elif primitive_name == "pseudonymize":
                res = fn(
                    col,
                    value or "",
                    tenant_id or "",
                    kv_client,
                    kwargs.get("salt_version"),
                )
            elif primitive_name == "as_is":
                res = fn(
                    col,
                    value if value is not None else kwargs.get("default"),
                    only_classes=tuple(
                        kwargs.get("only_classes", ("PUBLIC", "INTERNAL"))
                    ),
                    field_class=kwargs.get("field_class", "PUBLIC"),
                )
            elif primitive_name == "bucket":
                res = fn(col, value, kwargs.get("ranges", []))
            elif primitive_name == "aggregate":
                res = fn(
                    col,
                    kwargs.get("fn", "SUM"),
                    value if isinstance(value, list) else [value]
                    if value is not None
                    else [],
                )
            elif primitive_name == "score":
                res = fn(
                    kwargs.get("fields", {col: value or 0}),
                    kwargs.get("formula", "0"),
                )
            elif primitive_name == "keyword_flags":
                res = fn(col, value or "", kwargs.get("kw_dict", {}))
            else:  # pragma: no cover - registry membership already validated
                raise ValueError(f"unhandled primitive {primitive_name!r}")

            if res.field_class == "DROPPED":
                continue
            cols.append(col)
            exprs.append(res.expr)
            for k, val in res.params.items():
                params[k] = val

        sql = (
            f"INSERT INTO {self.target_table} ({', '.join(cols)}) "
            f"VALUES ({', '.join(exprs)})"
        )
        return sql, params


def _resolve_field(record: dict, path: str):
    """Resolve dotted field paths like ``company.id`` or ``types[]``.

    ``foo[]`` flattens a list of dicts/strings into a space-joined text run
    so keyword_flags can scan the concatenated text without each primitive
    needing to know about list shapes.
    """
    if not path:
        return None
    cur: Any = record
    for part in path.split("."):
        if "[]" in part:
            key = part.replace("[]", "")
            items = cur.get(key, []) if isinstance(cur, dict) else []
            if isinstance(items, list):
                return " ".join(
                    str(i.get("name", i)) if isinstance(i, dict) else str(i)
                    for i in items
                )
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None:
            return None
    return cur


def iter_all_recipes():
    """Discover every recipe under barycenter.etl.adapters.*. Used by the no-bypass CI gate.

    Plan 05 populates the connectwise.recipes module; until then this returns [].
    """
    recipes: list = []
    try:
        from barycenter.etl.adapters.connectwise.recipes import (  # type: ignore
            companies,
            agreements,
            tickets,
            configurations,
            time_entries,
        )
        for mod in (companies, agreements, tickets, configurations, time_entries):
            for attr in dir(mod):
                if attr.endswith("_recipe"):
                    recipes.append(getattr(mod, attr)())
    except ImportError:
        pass
    return recipes

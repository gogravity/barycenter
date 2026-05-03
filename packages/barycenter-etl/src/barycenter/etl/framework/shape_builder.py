"""ShapeBuilder: canonical-only writes to ai_zone (TOOL-03, Pitfall 8).

Adapters contribute INTO four fixed shapes; ShapeBuilder is the only writer to
ai_zone. A schema-time test (test_no_novel_ai_zone.py) asserts no other ai_zone
tables exist; this class is the runtime guard.
"""
from __future__ import annotations


class ShapeBuilder:
    CANONICAL = frozenset({
        "customer_snapshot",
        "customer_features_cw",
        "timeseries_aggregate",
        "customer_memory",
    })

    def populate(self, shape: str, sql_conn, audit=None) -> None:
        if shape not in self.CANONICAL:
            raise ValueError(
                f"refusing novel ai_zone shape: {shape!r} not in "
                f"{sorted(self.CANONICAL)}"
            )
        cur = sql_conn.cursor()
        cur.execute(f"TRUNCATE TABLE ai_zone.{shape}")
        cur.execute(self._build_sql(shape))
        sql_conn.commit()
        if audit is not None:
            from barycenter.etl.framework._audit_helpers import make_event
            audit.emit(make_event(
                verb="etl.shape.populate",
                resource_type=f"ai_zone.{shape}",
                outcome="success",
                metadata={"shape": shape},
            ))

    def _build_sql(self, shape: str) -> str:
        """Static SQL templates per shape. Phase 2 supports CW contributions only."""
        if shape == "customer_snapshot":
            return """
            INSERT INTO ai_zone.customer_snapshot
              (cw_company_id, tier, industry_bucket, employee_band, region,
               lifecycle_stage, ai_opt_out, cui_flag, synced_at)
            SELECT
              c.cw_company_id,
              NULL AS tier,
              NULL AS industry_bucket,
              NULL AS employee_band,
              c.billing_address_region AS region,
              NULL AS lifecycle_stage,
              c.ai_opt_out,
              c.cui_handling_required AS cui_flag,
              SYSUTCDATETIME()
            FROM raw_cw.companies c
            """
        if shape == "customer_features_cw":
            return """
            INSERT INTO ai_zone.customer_features_cw
              (cw_company_id, open_ticket_count, avg_age_days_bucket,
               top_keyword_flags, time_entries_h_30d_bucket, synced_at)
            SELECT
              t.cw_company_id,
              COUNT(*) AS open_ticket_count,
              NULL AS avg_age_days_bucket,
              NULL AS top_keyword_flags,
              NULL AS time_entries_h_30d_bucket,
              SYSUTCDATETIME()
            FROM raw_cw.tickets t
            WHERE t.status_name NOT IN ('Closed', 'Resolved', 'Cancelled')
            GROUP BY t.cw_company_id
            """
        if shape == "timeseries_aggregate":
            return """
            INSERT INTO ai_zone.timeseries_aggregate
              (cw_company_id, month, metric_name, value_bucketed, synced_at)
            SELECT
              cw_company_id,
              DATEFROMPARTS(YEAR(entry_date), MONTH(entry_date), 1) AS month,
              'time_hours' AS metric_name,
              CONVERT(NVARCHAR(64), SUM(total_hours)) AS value_bucketed,
              SYSUTCDATETIME()
            FROM raw_cw.time_entries
            GROUP BY cw_company_id,
                     DATEFROMPARTS(YEAR(entry_date), MONTH(entry_date), 1)
            """
        if shape == "customer_memory":
            # Phase 2: customer_memory populated sparsely from CW. Real population
            # arrives in Phase 3+ when agent-derived summaries land. Currently no-op.
            return "SELECT 1 WHERE 1 = 0"
        # Unreachable — CANONICAL membership checked above.
        raise ValueError(f"no SQL template for shape {shape!r}")

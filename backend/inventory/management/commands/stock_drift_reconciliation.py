"""
Management command: stock_drift_reconciliation
===============================================
Runs the Stock Drift Reconciliation audit and outputs a report.

Usage:
    python manage.py stock_drift_reconciliation
    python manage.py stock_drift_reconciliation --tolerance 0.01
    python manage.py stock_drift_reconciliation --product <uuid>
    python manage.py stock_drift_reconciliation --warehouse <uuid>
    python manage.py stock_drift_reconciliation --include-zero-stock
    python manage.py stock_drift_reconciliation --max-drifts 50
    python manage.py stock_drift_reconciliation --output report.json
    python manage.py stock_drift_reconciliation --quiet

Exit codes:
    0  — all batches clean (health_score == 100)
    1  — drift detected or error
"""
import json
import sys

from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError

from inventory.services.drift_reconciliation import StockDriftReconciliation


class Command(BaseCommand):
    help = "Run stock drift reconciliation audit and output a report"

    def add_arguments(self, parser):
        parser.add_argument(
            "--product", type=str, default=None,
            help="Filter by product UUID",
        )
        parser.add_argument(
            "--warehouse", type=str, default=None,
            help="Filter by warehouse UUID",
        )
        parser.add_argument(
            "--tolerance", type=str, default="0",
            help="Allowed drift before reporting (default: 0, exact match)",
        )
        parser.add_argument(
            "--include-zero-stock", action="store_true", default=False,
            help="Also check batches with remaining_quantity <= 0",
        )
        parser.add_argument(
            "--max-drifts", type=int, default=0,
            help="Stop after finding this many drifts (0 = no limit)",
        )
        parser.add_argument(
            "--output", "-o", type=str, default=None,
            help="Write JSON report to file (default: stdout only)",
        )
        parser.add_argument(
            "--quiet", "-q", action="store_true", default=False,
            help="Suppress human-readable output (useful with --output)",
        )

    def handle(self, **options):
        product_id = options["product"]
        warehouse_id = options["warehouse"]
        only_positive = not options["include_zero_stock"]
        max_drifts = options["max_drifts"]

        try:
            tolerance = Decimal(options["tolerance"])
        except Exception:
            raise CommandError(f"Invalid tolerance value: {options['tolerance']}")

        # Run reconciliation
        result = StockDriftReconciliation.run_full_reconciliation(
            product_id=product_id,
            warehouse_id=warehouse_id,
            tolerance=tolerance,
            only_positive_stock=only_positive,
            max_drifts=max_drifts,
        )

        # Build JSON-serialisable summary
        summary = {
            "is_healthy": result.is_healthy,
            "health_score": result.health_score,
            "total_batches_checked": result.total_batches_checked,
            "batches_clean": result.batches_clean,
            "batches_with_drift": result.batches_with_drift,
            "total_drift_value": str(result.total_drift_value),
            "truncated": result.truncated,
            "tolerance": str(tolerance),
            "filters": {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "only_positive_stock": only_positive,
                "max_drifts": max_drifts,
            },
            "drifts": [
                {
                    "batch_id": d.batch_id,
                    "batch_number": d.batch_number,
                    "product_name": d.product_name,
                    "warehouse_name": d.warehouse_name,
                    "stored_quantity": str(d.stored_quantity),
                    "computed_quantity": str(d.computed_quantity),
                    "drift_amount": str(d.drift_amount),
                    "movement_count": d.movement_count,
                }
                for d in result.drifts
            ],
        }

        # Write JSON output if requested
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, ensure_ascii=False)
            if not options["quiet"]:
                self.stdout.write(self.style.SUCCESS(
                    f"Report written to {options['output']}"
                ))

        # Human-readable report
        if not options["quiet"]:
            self._print_report(summary, result)

        # Exit code: 1 if drifts found, 0 otherwise
        if not result.is_healthy:
            sys.exit(1)

    def _print_report(self, summary, result):
        """Print a human-readable reconciliation report."""
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("  STOCK DRIFT RECONCILIATION REPORT")
        self.stdout.write("=" * 60)
        self.stdout.write("")

        # Health status
        if result.is_healthy:
            self.stdout.write(self.style.SUCCESS(
                f"  Status:  ✅ HEALTHY (score: {result.health_score}%)"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"  Status:  ⚠️  DRIFT DETECTED (score: {result.health_score}%)"
            ))

        # Summary counts
        self.stdout.write(f"  Checked: {result.total_batches_checked}")
        self.stdout.write(self.style.SUCCESS(
            f"  Clean:   {result.batches_clean}"
        ))
        if result.batches_with_drift > 0:
            self.stdout.write(self.style.WARNING(
                f"  Drifts:  {result.batches_with_drift}"
            ))
        else:
            self.stdout.write(f"  Drifts:  {result.batches_with_drift}")
        self.stdout.write(f"  Total drift (abs): {result.total_drift_value}")

        if result.truncated:
            self.stdout.write(self.style.WARNING(
                "\n  ⚠ Result TRUNCATED — some batches were not checked."
            ))

        # Filter info
        filters = summary["filters"]
        active_filters = []
        if filters["product_id"]:
            active_filters.append(f"product={filters['product_id']}")
        if filters["warehouse_id"]:
            active_filters.append(f"warehouse={filters['warehouse_id']}")
        if active_filters:
            self.stdout.write(f"\n  Filters: {', '.join(active_filters)}")

        # Drift details
        if result.drifts:
            self.stdout.write("")
            self.stdout.write("-" * 60)
            self.stdout.write("  DRIFT DETAILS")
            self.stdout.write("-" * 60)
            for d in result.drifts:
                self.stdout.write("")
                self.stdout.write(self.style.WARNING(
                    f"  Batch: {d.batch_number} ({d.product_name})"
                ))
                self.stdout.write(f"    Warehouse:   {d.warehouse_name or '(none)'}")
                self.stdout.write(f"    Stored:      {d.stored_quantity}")
                self.stdout.write(f"    Computed:    {d.computed_quantity}")
                self.stdout.write(f"    Drift:       {d.drift_amount}")
                self.stdout.write(f"    Movements:   {d.movement_count}")
        else:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(
                "  No drift detected. All batches are consistent."
            ))

        self.stdout.write("")
        self.stdout.write("=" * 60)

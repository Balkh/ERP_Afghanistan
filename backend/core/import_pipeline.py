"""Bulk import pipeline for Pharmacy ERP.

Supports CSV and Excel (.xlsx) imports for Products, Customers, and Suppliers.
Features: dry-run validation, duplicate detection, transactional import,
rollback on failure, row-level error reporting, bounded memory processing.
"""
import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from django.db import transaction


# ─── Field mappings ───────────────────────────────────────────────────────────

PRODUCT_FIELD_MAP = {
    'name': 'name',
    'product_name': 'name',
    'generic_name': 'generic_name',
    'brand_name': 'brand_name',
    'category': 'category',
    'unit': 'unit',
    'strength': 'strength',
    'form': 'form',
    'manufacturer': 'manufacturer',
    'barcode': 'barcode',
    'sku': 'sku',
    'description': 'description',
    'requires_prescription': 'requires_prescription',
    'is_controlled_substance': 'is_controlled_substance',
}

CUSTOMER_FIELD_MAP = {
    'name': 'name',
    'customer_name': 'name',
    'code': 'code',
    'customer_type': 'customer_type',
    'email': 'email',
    'phone': 'phone',
    'address': 'address',
    'city': 'city',
    'country': 'country',
    'national_id': 'national_id',
    'company_name': 'company_name',
    'tax_number': 'tax_number',
    'contact_person': 'contact_person',
    'contact_phone': 'contact_phone',
    'contact_email': 'contact_email',
    'credit_limit': 'credit_limit',
    'payment_terms_days': 'payment_terms_days',
    'notes': 'notes',
}

SUPPLIER_FIELD_MAP = {
    'name': 'name',
    'supplier_name': 'name',
    'code': 'code',
    'email': 'email',
    'phone': 'phone',
    'address': 'address',
    'city': 'city',
    'country': 'country',
    'company_name': 'company_name',
    'tax_number': 'tax_number',
    'contact_person': 'contact_person',
    'contact_phone': 'contact_phone',
    'contact_email': 'contact_email',
    'bank_name': 'bank_name',
    'bank_account': 'bank_account',
    'supply_categories': 'supply_categories',
    'lead_time_days': 'lead_time_days',
    'payment_terms_days': 'payment_terms_days',
    'notes': 'notes',
}

BOOL_FIELDS = {'requires_prescription', 'is_controlled_substance', 'is_active'}
DECIMAL_FIELDS = {'credit_limit', 'balance', 'payment_terms_days',
                  'lead_time_days', 'minimum_order_value', 'quality_rating'}

# Duplicate detection fields
PRODUCT_UNIQUE_FIELDS = ['barcode', 'sku', 'name']
CUSTOMER_UNIQUE_FIELDS = ['code', 'email', 'national_id', 'name']
SUPPLIER_UNIQUE_FIELDS = ['code', 'email', 'tax_number', 'name']


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class RowValidationResult:
    row_number: int
    data: dict
    is_valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    is_duplicate: bool = False


@dataclass
class ImportSummary:
    entity_type: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    imported_count: int
    errors: list = field(default_factory=list)
    row_results: list = field(default_factory=list)

    @property
    def success_rate(self):
        if self.total_rows == 0:
            return 0.0
        return round((self.valid_rows / self.total_rows) * 100, 1)


# ─── File parser ──────────────────────────────────────────────────────────────

class FileParser:
    """Parse CSV and Excel files with bounded memory usage."""

    CHUNK_SIZE = 500

    @classmethod
    def parse(cls, file_content: bytes, file_format: str, encoding: str = 'utf-8'):
        """Parse file content and yield rows as dicts.

        Args:
            file_content: raw file bytes
            file_format: 'csv' or 'xlsx'
            encoding: text encoding for CSV files

        Yields:
            dict: row data with header keys
        """
        if file_format == 'csv':
            yield from cls._parse_csv(file_content, encoding)
        elif file_format == 'xlsx':
            yield from cls._parse_xlsx(file_content)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    @classmethod
    def _parse_csv(cls, file_content: bytes, encoding: str):
        text = file_content.decode(encoding)
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            yield {k.strip().lower(): v.strip() for k, v in row.items() if k}

    @classmethod
    def _parse_xlsx(cls, file_content: bytes):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            wb.close()
            raise ValueError("No active sheet found")

        rows_iter = ws.iter_rows(values_only=True)
        try:
            headers = next(rows_iter)
        except StopIteration:
            wb.close()
            raise ValueError("Empty spreadsheet")

        headers = [str(h).strip().lower() if h else '' for h in headers]
        headers = [h for h in headers if h]

        for row in rows_iter:
            if all(cell is None for cell in row):
                continue
            yield {headers[i]: str(row[i]).strip() for i in range(min(len(headers), len(row))) if row[i] is not None}

        wb.close()


# ─── Validator ────────────────────────────────────────────────────────────────

class ImportValidator:
    """Validate rows against model constraints and detect duplicates."""

    def __init__(self, entity_type: str, field_map: dict, unique_fields: list, model_class):
        self.entity_type = entity_type
        self.field_map = field_map
        self.unique_fields = unique_fields
        self.model_class = model_class
        self._existing_values = self._load_existing_values()

    def _load_existing_values(self):
        existing = {}
        for uf in self.unique_fields:
            mapped = self.field_map.get(uf, uf)
            if hasattr(self.model_class, mapped):
                values = set(
                    self.model_class.objects.filter(**{f'{mapped}__isnull': False})
                    .values_list(mapped, flat=True)
                )
                existing[mapped] = values
        return existing

    def validate_row(self, row: dict, row_number: int) -> RowValidationResult:
        errors = []
        warnings = []
        mapped_data = {}

        for header, value in row.items():
            if not value:
                continue
            model_field = self.field_map.get(header)
            if model_field is None:
                warnings.append(f"Row {row_number}: Unknown column '{header}' ignored")
                continue

            if model_field in BOOL_FIELDS:
                mapped_data[model_field] = value.lower() in ('true', '1', 'yes')
            elif model_field in DECIMAL_FIELDS:
                try:
                    mapped_data[model_field] = Decimal(value)
                except (InvalidOperation, ValueError):
                    errors.append(f"Row {row_number}: Invalid decimal value for '{header}': {value}")
            else:
                mapped_data[model_field] = value

        if not mapped_data.get('name'):
            errors.append(f"Row {row_number}: 'name' is required")

        if not errors:
            dup_field = self._check_duplicate(mapped_data)
            if dup_field:
                return RowValidationResult(
                    row_number=row_number, data=mapped_data,
                    is_valid=False, is_duplicate=True,
                    errors=[f"Row {row_number}: Duplicate {dup_field}='{mapped_data.get(dup_field)}'"]
                )

        return RowValidationResult(
            row_number=row_number, data=mapped_data,
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _check_duplicate(self, data: dict) -> Optional[str]:
        for uf in self.unique_fields:
            mapped = self.field_map.get(uf, uf)
            if mapped in data and mapped in self._existing_values:
                if data[mapped] in self._existing_values[mapped]:
                    return mapped
        return None


# ─── Import engine ────────────────────────────────────────────────────────────

class BulkImportEngine:
    """Orchestrate bulk imports with transactional safety."""

    ENTITY_CONFIG = {
        'product': {
            'field_map': PRODUCT_FIELD_MAP,
            'unique_fields': PRODUCT_UNIQUE_FIELDS,
            'model': 'inventory.Product',
        },
        'customer': {
            'field_map': CUSTOMER_FIELD_MAP,
            'unique_fields': CUSTOMER_UNIQUE_FIELDS,
            'model': 'sales.Customer',
        },
        'supplier': {
            'field_map': SUPPLIER_FIELD_MAP,
            'unique_fields': SUPPLIER_UNIQUE_FIELDS,
            'model': 'purchases.Supplier',
        },
    }

    def __init__(self, entity_type: str, company=None):
        if entity_type not in self.ENTITY_CONFIG:
            raise ValueError(f"Unknown entity type: {entity_type}. Must be one of: {list(self.ENTITY_CONFIG.keys())}")

        self.entity_type = entity_type
        self.company = company
        config = self.ENTITY_CONFIG[entity_type]
        self.model = self._load_model(config['model'])
        self.validator = ImportValidator(
            entity_type, config['field_map'], config['unique_fields'], self.model
        )

    @staticmethod
    def _load_model(model_path: str):
        app_label, model_name = model_path.split('.')
        from django.apps import apps
        return apps.get_model(app_label, model_name)

    def dry_run(self, file_content: bytes, file_format: str) -> ImportSummary:
        """Validate file without importing. Returns full summary."""
        summary = ImportSummary(entity_type=self.entity_type, total_rows=0,
                                valid_rows=0, invalid_rows=0, duplicate_rows=0, imported_count=0)

        for row in FileParser.parse(file_content, file_format):
            summary.total_rows += 1
            result = self.validator.validate_row(row, summary.total_rows)
            summary.row_results.append(result)

            if result.is_duplicate:
                summary.duplicate_rows += 1
                summary.invalid_rows += 1
            elif result.is_valid:
                summary.valid_rows += 1
            else:
                summary.invalid_rows += 1

            summary.errors.extend(result.errors)

        return summary

    @transaction.atomic
    def execute(self, file_content: bytes, file_format: str) -> ImportSummary:
        """Import all valid rows transactionally. Rolls back on any failure."""
        summary = self.dry_run(file_content, file_format)

        if summary.valid_rows == 0:
            summary.errors.append("No valid rows to import")
            return summary

        imported = 0
        for result in summary.row_results:
            if not result.is_valid or result.is_duplicate:
                continue

            try:
                obj_data = result.data.copy()
                if self.company:
                    obj_data['company'] = self.company
                self.model.objects.create(**obj_data)
                imported += 1
                self.validator._existing_values = self.validator._load_existing_values()
            except Exception as e:
                summary.errors.append(f"Row {result.row_number}: Import failed - {str(e)}")
                raise

        summary.imported_count = imported
        return summary

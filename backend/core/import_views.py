"""Bulk import API views for Pharmacy ERP."""
import mimetypes

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from core.import_pipeline import BulkImportEngine


@api_view(['POST'])
@parser_classes([MultiPartParser])
def import_dry_run(request, entity_type):
    """Validate import file without committing changes."""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = request.FILES['file']
    file_content = uploaded_file.read()
    file_format = _detect_format(uploaded_file.name)

    try:
        company = getattr(request, 'company', None)
        engine = BulkImportEngine(entity_type, company=company)
        summary = engine.dry_run(file_content, file_format)

        return Response({
            'success': True,
            'summary': {
                'entity_type': summary.entity_type,
                'total_rows': summary.total_rows,
                'valid_rows': summary.valid_rows,
                'invalid_rows': summary.invalid_rows,
                'duplicate_rows': summary.duplicate_rows,
                'success_rate': summary.success_rate,
                'errors': summary.errors[:50],
            },
            'row_details': [
                {
                    'row_number': r.row_number,
                    'is_valid': r.is_valid,
                    'is_duplicate': r.is_duplicate,
                    'errors': r.errors,
                    'warnings': r.warnings,
                }
                for r in summary.row_results
            ],
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Validation failed: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@parser_classes([MultiPartParser])
def import_execute(request, entity_type):
    """Execute import transactionally. Rolls back on any failure."""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = request.FILES['file']
    file_content = uploaded_file.read()
    file_format = _detect_format(uploaded_file.name)

    try:
        company = getattr(request, 'company', None)
        engine = BulkImportEngine(entity_type, company=company)
        summary = engine.execute(file_content, file_format)

        return Response({
            'success': True,
            'summary': {
                'entity_type': summary.entity_type,
                'total_rows': summary.total_rows,
                'valid_rows': summary.valid_rows,
                'invalid_rows': summary.invalid_rows,
                'duplicate_rows': summary.duplicate_rows,
                'imported_count': summary.imported_count,
                'success_rate': summary.success_rate,
                'errors': summary.errors[:50],
            },
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Import failed (rolled back): {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _detect_format(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    if mime == 'text/csv' or filename.lower().endswith('.csv'):
        return 'csv'
    if mime or filename.lower().endswith(('.xlsx', '.xls')):
        return 'xlsx'
    raise ValueError(f"Unsupported file type: {filename}. Use .csv or .xlsx")

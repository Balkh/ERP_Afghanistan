"""
Standardized JSON Renderer.
Automatically wraps all DRF responses in standardized format.
"""
import uuid
from datetime import datetime
from rest_framework.renderers import JSONRenderer
from core.multitenant.context import TenantContext


class StandardizedJSONRenderer(JSONRenderer):
    """
    Renderer that automatically wraps all responses in standardized format:
    {
        "success": true,
        "data": {...},
        "meta": {
            "request_id": "uuid",
            "timestamp": "ISO8601",
            "company_id": "uuid" (if available)
        }
    }
    """
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            data = {}
        
        response = renderer_context.get('response')
        view = renderer_context.get('view')
        
        company_id = TenantContext.get_company_id()
        
        meta = {
            'request_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }
        
        if company_id:
            meta['company_id'] = str(company_id)
        
        if hasattr(response, 'observability_read_only') and response.observability_read_only:
            meta['read_only'] = True
        
        if hasattr(response, 'observability_meta_extras') and response.observability_meta_extras:
            meta.update(response.observability_meta_extras)
        
        if hasattr(response, 'status_code'):
            if 200 <= response.status_code < 300:
                standard_response = {
                    'success': True,
                    'data': data,
                    'meta': meta
                }
                
                if hasattr(response, 'status_code') and response.status_code == 204:
                    return super().render({}, accepted_media_type, renderer_context)
                    
            else:
                standard_response = {
                    'success': False,
                    'error': data if isinstance(data, dict) else {'message': str(data)},
                    'meta': meta
                }
        else:
            standard_response = {
                'success': True,
                'data': data,
                'meta': meta
            }
        
        return super().render(standard_response, accepted_media_type, renderer_context)
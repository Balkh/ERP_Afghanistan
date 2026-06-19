"""Regression: tenant membership must be enforced for JWT (Bearer) requests.

DRF JWT auth runs at the view layer, so request.user is AnonymousUser while
TenantMiddleware executes. Previously this caused the membership check to be
skipped, letting a user of company A pivot to company B via X-Company-ID.
"""
import uuid

import pytest
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.test import RequestFactory

from core.models import Company
from core.models.multitenant import UserCompanyMapping
from core.multitenant.context import TenantContext
from core.multitenant.middleware import TenantMiddleware
from security.authentication import generate_jwt_token


def _company(name):
    return Company.objects.create(
        name=name, code=f'C{uuid.uuid4().hex[:6]}'.upper(),
        registration_number=f'REG-{uuid.uuid4().hex[:8]}',
        address='x', phone='+10000000000',
        email=f'{uuid.uuid4().hex[:6]}@t.com', is_active=True,
    )


def _capture_context_middleware():
    """Build a TenantMiddleware whose downstream handler records the company
    context that was active during the request."""
    seen = {}

    def get_response(request):
        seen['company_id'] = TenantContext.get_company_id()
        return JsonResponse({'ok': True})

    return TenantMiddleware(get_response), seen


def _bearer_request(company_header_id, token):
    rf = RequestFactory()
    return rf.get(
        '/api/customers/',
        HTTP_AUTHORIZATION=f'Bearer {token}',
        HTTP_X_COMPANY_ID=str(company_header_id),
    )


@pytest.mark.django_db
def test_mapped_user_cannot_pivot_to_other_company():
    company_a = _company('Company A')
    company_b = _company('Company B')
    user = User.objects.create_user(username=f'u{uuid.uuid4().hex[:6]}', password='x')
    UserCompanyMapping.objects.create(user=user, company=company_a, is_active=True, is_default=True)

    token = generate_jwt_token(user, tenant_id=str(company_a.id))
    mw, seen = _capture_context_middleware()

    # Attempt to access company B via header -> must be denied (403).
    resp = mw(_bearer_request(company_b.id, token))
    assert resp.status_code == 403
    # Context must NOT have been set to company B for the downstream view.
    assert seen.get('company_id') != str(company_b.id)


@pytest.mark.django_db
def test_mapped_user_can_access_own_company():
    company_a = _company('Company A')
    user = User.objects.create_user(username=f'u{uuid.uuid4().hex[:6]}', password='x')
    UserCompanyMapping.objects.create(user=user, company=company_a, is_active=True, is_default=True)

    token = generate_jwt_token(user, tenant_id=str(company_a.id))
    mw, seen = _capture_context_middleware()

    resp = mw(_bearer_request(company_a.id, token))
    assert resp.status_code == 200
    assert seen.get('company_id') == str(company_a.id)


@pytest.mark.django_db
def test_unmapped_user_is_backward_compatible():
    """A user with no company mappings (legacy/single-tenant) is not blocked."""
    company_a = _company('Company A')
    user = User.objects.create_user(username=f'u{uuid.uuid4().hex[:6]}', password='x')
    # No UserCompanyMapping rows for this user.

    token = generate_jwt_token(user)
    mw, seen = _capture_context_middleware()

    resp = mw(_bearer_request(company_a.id, token))
    assert resp.status_code == 200
    assert seen.get('company_id') == str(company_a.id)

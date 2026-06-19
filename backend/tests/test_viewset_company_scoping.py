"""Regression: ViewSet get_queryset overrides must not bypass company scoping.

Covers the previously-unscoped paths:
  - CustomerViewSet with ?include_inactive=true (returned Customer.objects.all())
  - DepartmentViewSet (returned Department.objects.all(), skipping super())
"""
import uuid

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from core.models import Company
from core.multitenant.context import TenantContext
from sales.models import Customer
from sales.views import CustomerViewSet
from hr.models import Department
from hr.views import DepartmentViewSet


def _company(name):
    return Company.objects.create(
        name=name, code=f'C{uuid.uuid4().hex[:6]}'.upper(),
        registration_number=f'REG-{uuid.uuid4().hex[:8]}', is_active=True,
    )


def _customer(company, name, active=True):
    c = Customer(company=company, name=name, code=f'K{uuid.uuid4().hex[:6]}',
                 phone='+10000000000', is_active=active)
    c.save()
    return c


@pytest.mark.django_db
def test_customer_include_inactive_stays_company_scoped():
    a = _company('A')
    b = _company('B')
    _customer(a, 'A-active', active=True)
    _customer(a, 'A-inactive', active=False)
    _customer(b, 'B-active', active=True)
    _customer(b, 'B-inactive', active=False)

    from rest_framework.request import Request
    rf = APIRequestFactory()
    view = CustomerViewSet()
    view.request = Request(rf.get('/api/customers/?include_inactive=true'))
    view.request.user = AnonymousUser()
    view.format_kwarg = None
    view.kwargs = {}

    TenantContext.set_company_id(str(a.id))
    try:
        qs = view.get_queryset()
        companies = {str(c.company_id) for c in qs}
        names = sorted(c.name for c in qs)
    finally:
        TenantContext.clear()

    # Only company A's customers, and inactive ones ARE included.
    assert companies == {str(a.id)}
    assert names == ['A-active', 'A-inactive']


@pytest.mark.django_db
def test_department_listing_is_company_scoped():
    a = _company('A')
    b = _company('B')
    Department.objects.create(company=a, name='A-Dept', code=f'D{uuid.uuid4().hex[:5]}')
    Department.objects.create(company=b, name='B-Dept', code=f'D{uuid.uuid4().hex[:5]}')

    from rest_framework.request import Request
    rf = APIRequestFactory()
    view = DepartmentViewSet()
    view.request = Request(rf.get('/api/departments/'))
    view.request.user = AnonymousUser()
    view.format_kwarg = None
    view.kwargs = {}

    TenantContext.set_company_id(str(a.id))
    try:
        qs = view.get_queryset()
        companies = {str(d.company_id) for d in qs}
    finally:
        TenantContext.clear()

    assert companies == {str(a.id)}

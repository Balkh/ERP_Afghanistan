"""
Multi-Company Security Integration.
Users can belong to multiple companies with company-specific roles.
"""
from typing import List, Optional
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from core.models.base import BaseModel
from core.models.system import Company

User = get_user_model()


class UserCompanyMapping(BaseModel):
    """
    Maps users to companies with company-specific roles.
    A user can belong to multiple companies, each with a different role.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='company_mappings',
        verbose_name='User',
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='user_mappings',
        verbose_name='Company',
    )
    role_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Role Name',
        help_text='Role for this company (e.g., ADMIN, MANAGER, ACCOUNTANT)',
    )
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    is_default = models.BooleanField(default=False, verbose_name='Is Default Company')

    class Meta:
        verbose_name = 'User Company Mapping'
        verbose_name_plural = 'User Company Mappings'
        unique_together = ['user', 'company']
        ordering = ['company__name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.company.code} ({self.role_name})"

    def clean(self):
        if self.is_default:
            existing = UserCompanyMapping.objects.filter(
                user=self.user, is_default=True
            ).exclude(id=self.id)
            if existing.exists():
                raise ValidationError('Only one default company per user allowed.')


class CompanyPermissionService:
    """
    Service for checking company-scoped permissions.
    """

    @staticmethod
    def get_user_companies(user) -> List[Company]:
        """Get all companies a user has access to."""
        mappings = UserCompanyMapping.objects.filter(
            user=user, is_active=True
        ).select_related('company')
        return [m.company for m in mappings]

    @staticmethod
    def get_user_role_in_company(user, company_id: str) -> Optional[str]:
        """Get user's role name for a specific company."""
        mapping = UserCompanyMapping.objects.filter(
            user=user, company_id=company_id, is_active=True
        ).first()
        return mapping.role_name if mapping else None

    @staticmethod
    def has_company_access(user, company_id: str) -> bool:
        """Check if user has access to a company."""
        return UserCompanyMapping.objects.filter(
            user=user, company_id=company_id, is_active=True
        ).exists()

    @staticmethod
    def get_default_company(user) -> Optional[Company]:
        """Get user's default company."""
        mapping = UserCompanyMapping.objects.filter(
            user=user, is_active=True, is_default=True
        ).select_related('company').first()
        if mapping:
            return mapping.company
        first_mapping = UserCompanyMapping.objects.filter(
            user=user, is_active=True
        ).select_related('company').first()
        return first_mapping.company if first_mapping else None

    @staticmethod
    def auto_assign_default_company(user):
        """Assign user to the first company if no mappings exist."""
        if not UserCompanyMapping.objects.filter(user=user).exists():
            first_company = Company.objects.active()
            if first_company:
                UserCompanyMapping.objects.create(
                    user=user,
                    company=first_company,
                    is_default=True,
                    role_name='ADMIN',
                )

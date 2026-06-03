import logging
import os
import sys
import time
import uuid
import threading
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

"""SECTION: Security Hardening — extracted from migration_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
from production_infrastructure.migration_validator import (
    InfraIssue, SectionResult, CRITICAL, HIGH, MEDIUM, LOW, logger,
)


def run(self) -> SectionResult:
    issues: List[InfraIssue] = []
    try:
        from django.conf import settings

        https_checks = {
            "SESSION_COOKIE_SECURE": getattr(settings, "SESSION_COOKIE_SECURE", False),
            "CSRF_COOKIE_SECURE": getattr(settings, "CSRF_COOKIE_SECURE", False),
            "SECURE_SSL_REDIRECT": getattr(settings, "SECURE_SSL_REDIRECT", False),
            "SECURE_HSTS_SECONDS": getattr(settings, "SECURE_HSTS_SECONDS", 0) > 0,
        }
        https_pass = all(https_checks.values())
        if https_pass:
            issues.append(InfraIssue(
                section="security_hardening", severity=LOW,
                check="https_config", detail="All HTTPS security settings enabled", passed=True,
            ))
        else:
            disabled = [k for k, v in https_checks.items() if not v]
            issues.append(InfraIssue(
                section="security_hardening", severity=MEDIUM,
                check="https_config", detail=f"HTTPS settings disabled: {disabled}",
            ))

        xss_checks = {
            "SECURE_BROWSER_XSS_FILTER": getattr(settings, "SECURE_BROWSER_XSS_FILTER", False),
            "SECURE_CONTENT_TYPE_NOSNIFF": getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False),
            "X_FRAME_OPTIONS": getattr(settings, "X_FRAME_OPTIONS", "") == "DENY",
        }
        xss_pass = all(xss_checks.values())
        if xss_pass:
            issues.append(InfraIssue(
                section="security_hardening", severity=LOW,
                check="xss_protection", detail="XSS/clickjacking protection enabled", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="security_hardening", severity=MEDIUM,
                check="xss_protection", detail="Some XSS protections disabled",
            ))

        from security.authentication import generate_jwt_token, generate_refresh_token
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.first()
        if user:
            token = generate_jwt_token(user)
            refresh = generate_refresh_token(user)
            if token and refresh:
                issues.append(InfraIssue(
                    section="security_hardening", severity=LOW,
                    check="jwt_generation", detail="JWT token generation works", passed=True,
                ))
        else:
            issues.append(InfraIssue(
                section="security_hardening", severity=MEDIUM,
                check="jwt_generation", detail="No users for JWT test",
            ))

        from security.authentication import verify_jwt_token
        if user and token:
            try:
                payload = verify_jwt_token(token)
                if payload and payload.get("token_type") == "access":
                    issues.append(InfraIssue(
                        section="security_hardening", severity=LOW,
                        check="jwt_verification", detail="JWT token verification works", passed=True,
                    ))
            except Exception as e:
                issues.append(InfraIssue(
                    section="security_hardening", severity=MEDIUM,
                    check="jwt_verification", detail=f"JWT verification: {e}",
                ))

        from security.models import RevokedToken
        from django.utils import timezone
        rt = RevokedToken.revoke(
            jti=str(uuid.uuid4()),
            token_type="refresh",
            expires_at=timezone.now() + timedelta(hours=1),
            reason="logout",
        )
        if rt:
            issues.append(InfraIssue(
                section="security_hardening", severity=LOW,
                check="token_revocation", detail="Token revocation and blacklist works", passed=True,
            ))

        from security.permissions import RoleBasedPermission
        issues.append(InfraIssue(
            section="security_hardening", severity=LOW,
            check="rbac", detail="RBAC permission class available", passed=True,
        ))

        from security.rate_limiter import RateLimitMiddleware
        has_middleware = any(
            "RateLimit" in m for m in getattr(settings, "MIDDLEWARE", [])
        )
        if has_middleware:
            issues.append(InfraIssue(
                section="security_hardening", severity=LOW,
                check="rate_limiting", detail="Rate limiting active", passed=True,
            ))

        cors = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        if cors:
            issues.append(InfraIssue(
                section="security_hardening", severity=LOW,
                check="cors", detail=f"CORS configured: {len(cors)} origins", passed=True,
            ))

    except Exception as e:
        issues.append(InfraIssue(
            section="security_hardening", severity=CRITICAL,
            check="validator_crash", detail=f"Security hardening crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (CRITICAL, HIGH)]) == 0
    self.results["security_hardening"] = SectionResult(
        name="Security Hardening", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues",
    )
    self.issues.extend(issues)
    return self.results["security_hardening"]

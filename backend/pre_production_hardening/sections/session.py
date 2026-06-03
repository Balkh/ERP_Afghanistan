"""
SECTION 4: SESSION + AUTH HARDENING
Extracted from PreProductionHardeningValidator.validate_session_security
"""
import uuid
from datetime import timedelta

from pre_production_hardening.hardening_validator import (
    HardeningIssue, SectionResult,
    ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW,
)


def run(validator) -> SectionResult:
    issues: list = []
    try:
        from django.conf import settings
        from security.authentication import (
            generate_jwt_token, generate_refresh_token,
        )
        from security.models import RevokedToken

        # Check JWT expiry configuration
        if hasattr(settings, "SIMPLE_JWT"):
            jwt_settings = settings.SIMPLE_JWT
            access_lifetime = jwt_settings.get("ACCESS_TOKEN_LIFETIME", None)
            if access_lifetime:
                issues.append(HardeningIssue(
                    section="session_security", severity=ISSUE_LOW,
                    check="jwt_config", detail=f"JWT access lifetime: {access_lifetime}", passed=True,
                ))
        else:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_LOW,
                check="jwt_config",
                detail="Using custom JWT authentication (security/authentication.py)", passed=True,
            ))

        # Test token generation and validation
        from django.contrib.auth import get_user_model
        User = get_user_model()
        test_user = User.objects.first()
        if not test_user:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_MEDIUM,
                check="token_generation", detail="No users available for token generation test",
            ))
            test_user_id = str(uuid.uuid4())
            test_company_id = str(uuid.uuid4())
        else:
            test_user_id = test_user.id
            test_company_id = str(uuid.uuid4())

        if test_user:
            token = generate_jwt_token(test_user, test_company_id)
            refresh = generate_refresh_token(test_user)

            if token and refresh:
                issues.append(HardeningIssue(
                    section="session_security", severity=ISSUE_LOW,
                    check="token_generation", detail="JWT token generation works", passed=True,
                ))
            else:
                issues.append(HardeningIssue(
                    section="session_security", severity=ISSUE_HIGH,
                    check="token_generation", detail="JWT token generation failed",
                ))

        # Test token revocation
        try:
            from django.utils import timezone
            rt = RevokedToken.revoke(
                jti=str(uuid.uuid4()),
                token_type="access",
                expires_at=timezone.now() + timedelta(hours=1),
                reason="logout",
            )
            if rt and rt.id:
                issues.append(HardeningIssue(
                    section="session_security", severity=ISSUE_LOW,
                    check="token_revocation", detail="Token revocation storage works", passed=True,
                ))
            else:
                issues.append(HardeningIssue(
                    section="session_security", severity=ISSUE_MEDIUM,
                    check="token_revocation", detail="Token revocation returned no record",
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_MEDIUM,
                check="token_revocation", detail=f"Token revocation storage failed: {e}",
            ))

        # Check password hashers
        password_hashers = getattr(settings, "PASSWORD_HASHERS", [])
        has_secure_hasher = any(
            "Argon2" in h or "PBKDF2" in h or "BCrypt" in h for h in password_hashers
        )
        if has_secure_hasher:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_LOW,
                check="password_hashing", detail="Secure password hasher configured", passed=True,
            ))
        elif not password_hashers:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_LOW,
                check="password_hashing",
                detail="Default Django password hashers (PBKDF2)", passed=True,
            ))

        # Check session security settings
        session_secure = getattr(settings, "SESSION_COOKIE_SECURE", False)
        session_httponly = getattr(settings, "SESSION_COOKIE_HTTPONLY", True)
        csrf_cookie_secure = getattr(settings, "CSRF_COOKIE_SECURE", False)

        if not session_secure:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_MEDIUM,
                check="session_cookie_secure",
                detail="SESSION_COOKIE_SECURE=False. Set to True in production for HTTPS.",
            ))
        else:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_LOW,
                check="session_cookie_secure", detail="SESSION_COOKIE_SECURE=True", passed=True,
            ))

        if not session_httponly:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_MEDIUM,
                check="session_cookie_httponly",
                detail="SESSION_COOKIE_HTTPONLY=False. JavaScript can access session cookie.",
            ))
        else:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_LOW,
                check="session_cookie_httponly", detail="SESSION_COOKIE_HTTPONLY=True", passed=True,
            ))

        # Check rate limiting
        if hasattr(settings, "RATE_LIMIT_CONFIG"):
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_LOW,
                check="rate_limiting", detail="Rate limiting configured", passed=True,
            ))
        else:
            rate_middleware = "security.rate_limiter.RateLimitMiddleware"
            middleware = getattr(settings, "MIDDLEWARE", [])
            if rate_middleware in middleware:
                issues.append(HardeningIssue(
                    section="session_security", severity=ISSUE_LOW,
                    check="rate_limiting", detail="RateLimitMiddleware registered", passed=True,
                ))

        # Check CORS
        cors_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        if not cors_origins:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_MEDIUM,
                check="cors_config",
                detail="CORS_ALLOWED_ORIGINS not configured. May be open in production.",
            ))
        else:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_LOW,
                check="cors_config", detail=f"CORS configured: {len(cors_origins)} origins", passed=True,
            ))

        # Check RBAC permission classes
        rest_fw_settings = getattr(settings, "REST_FRAMEWORK", {})
        default_perms = rest_fw_settings.get("DEFAULT_PERMISSION_CLASSES", [])
        if "IsAuthenticated" in str(default_perms) or "IsAuthenticated" in " ".join(default_perms):
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_LOW,
                check="auth_default", detail="Default auth: IsAuthenticated", passed=True,
            ))
        else:
            issues.append(HardeningIssue(
                section="session_security", severity=ISSUE_MEDIUM,
                check="auth_default",
                detail="Default permission class may not require authentication",
                evidence={"default_permissions": default_perms},
            ))

    except Exception as e:
        issues.append(HardeningIssue(
            section="session_security", severity=ISSUE_CRITICAL,
            check="session_crash", detail=f"Session security validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    validator.results["session_security"] = SectionResult(
        name="Session + Auth Hardening", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues found",
    )
    validator.issues.extend(issues)
    return validator.results["session_security"]

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from security.models import AuditLog, UserRole
from security.authentication import generate_jwt_token, generate_refresh_token, verify_jwt_token
from security.ui_scopes import resolve_ui_scopes
from security.permissions import RoleBasedPermission
from core.api.responses import APIResponse
from core.api.errors import ErrorCode, create_error_response, get_status_for_error
from datetime import datetime, timedelta


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate user and return JWT token.
    Standardized response format.
    """
    from django.contrib.auth import authenticate
    
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            create_error_response(ErrorCode.VAL_001, "Username and password are required"),
            status=400
        )
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        AuditLog.objects.create(
            action='LOGIN_FAILED',
            username=username,
            ip_address=ip_address,
            additional_data={'username': username}
        )
        # Record failed login for rate limiting
        from security.rate_limiter import record_failed_login
        record_failed_login(ip_address)
        return Response(
            create_error_response(ErrorCode.AUTH_001, "Invalid credentials"),
            status=401
        )
    
    if not user.is_active:
        return Response(
            create_error_response(ErrorCode.AUTH_004, "Account is disabled"),
            status=401
        )
    
    # Get user roles
    user_roles = UserRole.objects.filter(
        user=user,
        expires_at__isnull=True
    ) | UserRole.objects.filter(
        user=user,
        expires_at__gt=datetime.now()
    )
    roles = [ur.role.name for ur in user_roles]
    
    # ── 2FA Enforcement (staged, role-based) ──
    requires_2fa = any(
        ur.role.require_2fa for ur in user_roles
    )
    
    if requires_2fa:
        from security.totp_service import TOTPService
        from security.models import TOTPDevice
        
        has_confirmed_device = TOTPService.is_enabled(user)
        totp_code = request.data.get('totp_code')
        
        if not has_confirmed_device:
            # User's role requires 2FA but no device is set up
            # Return a challenge indicating setup is required
            # Superusers are exempt from hard lockout (bootstrap safety)
            if not user.is_superuser:
                return Response(
                    create_error_response(
                        ErrorCode.AUTH_008,
                        "Your role requires 2FA. Please set up TOTP first."
                    ),
                    status=403
                )
        elif not totp_code:
            # Device exists but no TOTP code provided — challenge the user
            return Response(
                create_error_response(
                    ErrorCode.AUTH_009,
                    "2FA code required. Provide 'totp_code' in the request body."
                ),
                status=403
            )
        else:
            # Verify the TOTP code
            if not TOTPService.verify_code(user, totp_code):
                return Response(
                    create_error_response(ErrorCode.AUTH_001, "Invalid 2FA code"),
                    status=401
                )
    
    # Resolve UI scopes for frontend
    ui_scopes = resolve_ui_scopes(roles)
    
    access_token = generate_jwt_token(user, ui_scopes=ui_scopes)
    refresh_token = generate_refresh_token(user)
    
    # Reset rate limit on successful login
    from security.rate_limiter import reset_login_limit
    reset_login_limit(request.META.get('REMOTE_ADDR', 'unknown'))
    
    # Get user companies
    from core.models import Company
    from core.models.multitenant import UserCompanyMapping
    user_companies = UserCompanyMapping.objects.filter(
        user=user,
        is_active=True
    ).select_related('company')
    
    companies = [
        {
            "id": str(mapping.company.id),
            "name": mapping.company.name,
            "code": mapping.company.code,
            "role": mapping.role_name,
            "is_default": mapping.is_default
        }
        for mapping in user_companies
    ]
    
    # Default to first company if no default set
    if not any(c.get('is_default', False) for c in companies) and companies:
        companies[0]['is_default'] = True
    
    # Resolve UI scopes for frontend
    ui_scopes = resolve_ui_scopes(roles)
    
    # Log successful login
    AuditLog.objects.create(
        action='LOGIN',
        user=user,
        username=user.username,
        ip_address=request.META.get('REMOTE_ADDR', 'unknown'),
        additional_data={'username': username, 'roles': roles, 'ui_scopes': ui_scopes}
    )
    
    # Create login notification
    try:
        from security.notification_service import NotificationService
        NotificationService.notify_user_login(user, ip_address=request.META.get('REMOTE_ADDR'))
    except Exception:
        pass
    
    # Return standardized response
    response_data = APIResponse.success(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 86400,  # 24 hours in seconds
            "ui_scopes": ui_scopes,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_superuser": user.is_superuser,
                "roles": roles,
                "companies": companies
            }
        },
        message="Login successful"
    )
    
    return Response(response_data, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """
    Refresh access token using refresh token.
    Returns new access + refresh tokens (token rotation).
    """
    raw_refresh_token = request.data.get('refresh_token')
    
    if not raw_refresh_token:
        return Response(
            create_error_response(ErrorCode.VAL_001, "Refresh token is required"),
            status=400
        )
    
    try:
        payload = verify_jwt_token(raw_refresh_token, expected_type='refresh')
    except Exception as e:
        return Response(
            create_error_response(ErrorCode.AUTH_002, str(e)),
            status=401
        )
    
    try:
        from django.contrib.auth.models import User
        user = User.objects.get(id=payload['user_id'], is_active=True)
    except User.DoesNotExist:
        return Response(
            create_error_response(ErrorCode.AUTH_003, "User not found or inactive"),
            status=401
        )
    
    # Get user roles for ui_scopes
    user_roles = UserRole.objects.filter(
        user=user,
        expires_at__isnull=True
    ) | UserRole.objects.filter(
        user=user,
        expires_at__gt=datetime.now()
    )
    roles = [ur.role.name for ur in user_roles]
    ui_scopes = resolve_ui_scopes(roles)
    
    new_access = generate_jwt_token(user, ui_scopes=ui_scopes)
    new_refresh = generate_refresh_token(user)
    
    return Response(APIResponse.success(
        data={
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "Bearer",
            "expires_in": 86400,
            "ui_scopes": ui_scopes,
        },
        message="Token refreshed successfully"
    ))


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    """Logout user and invalidate session."""
    if not request.user or not request.user.is_authenticated:
        return Response(
            create_error_response(ErrorCode.AUTH_003, "Authentication required"),
            status=401
        )
    
    # Revoke the current access token
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        from security.authentication import verify_jwt_token, blacklist_token
        try:
            payload = verify_jwt_token(auth_header.split(' ', 1)[1])
            jti = payload.get('jti')
            exp_str = payload.get('exp')
            if jti:
                from datetime import datetime
                exp = datetime.fromtimestamp(exp_str) if exp_str else None
                blacklist_token(jti, exp=exp)
        except Exception:
            pass  # Token may already be invalid — proceed with logout
    
    AuditLog.objects.create(
        action='LOGOUT',
        user=request.user,
        username=request.user.username,
        ip_address=request.META.get('REMOTE_ADDR', 'unknown'),
        additional_data={'username': request.user.username}
    )
    
    return Response(APIResponse.success(
        data=None,
        message="Logged out successfully"
    ))


@api_view(['GET'])
@permission_classes([AllowAny])
def user_profile(request):
    """Get current user profile."""
    if not request.user or not request.user.is_authenticated:
        return Response(
            create_error_response(ErrorCode.AUTH_003, "Authentication required"),
            status=401
        )
    
    user = request.user
    user_roles = UserRole.objects.filter(
        user=user,
        expires_at__isnull=True
    ) | UserRole.objects.filter(
        user=user,
        expires_at__gt=datetime.now()
    )
    roles = [ur.role for ur in user_roles]
    role_names = [r.name for r in roles]
    
    # Get permissions
    permissions = []
    for role in roles:
        for rp in role.role_permissions.select_related('permission').all():
            if rp.permission.codename not in permissions:
                permissions.append(rp.permission.codename)
    
    # Resolve UI scopes
    ui_scopes = resolve_ui_scopes(role_names)
    
    # Get companies
    from core.models.multitenant import UserCompanyMapping
    user_companies = UserCompanyMapping.objects.filter(
        user=user,
        is_active=True
    ).select_related('company')
    
    companies = [
        {
            "id": str(mapping.company.id),
            "name": mapping.company.name,
            "code": mapping.company.code,
            "role": mapping.role_name
        }
        for mapping in user_companies
    ]
    
    return Response(APIResponse.success(
        data={
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser,
            "roles": role_names,
            "permissions": permissions,
            "ui_scopes": ui_scopes,
            "companies": companies
        }
    ))


@api_view(['POST'])
@permission_classes([AllowAny])
def change_password(request):
    """Change user password."""
    from django.contrib.auth.password_validation import validate_password
    
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response(
            create_error_response(ErrorCode.VAL_001, "Old password and new password are required"),
            status=400
        )
    
    if not request.user.check_password(old_password):
        return Response(
            create_error_response(ErrorCode.AUTH_001, "Invalid old password"),
            status=400
        )
    
    try:
        validate_password(new_password, request.user)
    except Exception as e:
        return Response(
            create_error_response(ErrorCode.VAL_002, str(e)),
            status=400
        )
    
    request.user.set_password(new_password)
    request.user.save()
    
    AuditLog.objects.create(
        action='UPDATE',
        user=request.user,
        username=request.user.username,
        ip_address=request.META.get('REMOTE_ADDR', 'unknown'),
        additional_data={'action': 'password_change'}
    )
    
    return Response(APIResponse.success(
        data=None,
        message="Password changed successfully"
    ))


@api_view(['GET'])
@permission_classes([AllowAny])
def notifications_list(request):
    """Get all notifications for the current user."""
    from security.models import Notification
    from security.notification_service import NotificationService
    
    is_read = request.query_params.get('is_read')
    notification_type = request.query_params.get('type')
    
    notifications = Notification.objects.filter(user=request.user)
    
    if is_read is not None:
        notifications = notifications.filter(is_read=is_read.lower() == 'true')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    
    total = notifications.count()
    notifications_list = notifications[start:end]
    
    unread_count = NotificationService.get_unread_count(request.user)
    
    return Response(APIResponse.paginated(
        data=[
            {
                'id': str(n.id),
                'notification_type': n.notification_type,
                'severity': n.severity,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
            }
            for n in notifications_list
        ],
        page=page,
        page_size=page_size,
        total=total
    ))


@api_view(['POST'])
@permission_classes([AllowAny])
def notifications_mark_read(request):
    """Mark a notification as read."""
    from security.notification_service import NotificationService
    
    notification_id = request.data.get('notification_id')
    mark_all = request.data.get('mark_all', False)
    
    if mark_all:
        count = NotificationService.mark_all_as_read(request.user)
        return Response(APIResponse.success(
            data={"marked_count": count},
            message=f"Marked {count} notifications as read"
        ))
    
    if not notification_id:
        return Response(
            create_error_response(ErrorCode.VAL_001, "notification_id is required"),
            status=400
        )
    
    success = NotificationService.mark_as_read(notification_id, request.user)
    if not success:
        return Response(
            create_error_response("INV_003", "Notification not found"),
            status=404
        )
    
    return Response(APIResponse.success(
        data=None,
        message="Notification marked as read"
    ))


@api_view(['GET'])
@permission_classes([AllowAny])
def notifications_unread_count(request):
    """Get unread notification count."""
    from security.notification_service import NotificationService
    count = NotificationService.get_unread_count(request.user)
    return Response(APIResponse.success(data={"unread_count": count}))


@api_view(['GET', 'POST'])
@permission_classes([RoleBasedPermission])
def users_list(request):
    """List or create users."""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import User
    from core.models.multitenant import UserCompanyMapping

    if request.method == 'GET':
        if not request.user.is_superuser:
            return Response(
                create_error_response(ErrorCode.AUTH_002, "Permission denied"),
                status=403
            )

        search = request.query_params.get('search', '')
        is_active = request.query_params.get('is_active')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        users = User.objects.all().order_by('-date_joined')
        if search:
            users = users.filter(username__icontains=search) | users.filter(email__icontains=search)
        if is_active is not None:
            users = users.filter(is_active=is_active.lower() == 'true')

        total = users.count()
        start = (page - 1) * page_size
        users_page = users[start:start + page_size]

        return Response(APIResponse.paginated(
            data=[
                {
                    'id': str(u.id),
                    'username': u.username,
                    'email': u.email,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'is_active': u.is_active,
                    'is_superuser': u.is_superuser,
                    'date_joined': u.date_joined.isoformat(),
                    'roles': list(u.user_roles.values_list('role__name', flat=True))
                }
                for u in users_page
            ],
            page=page,
            page_size=page_size,
            total=total
        ))

    elif request.method == 'POST':
        if not request.user.is_superuser:
            return Response(
                create_error_response(ErrorCode.AUTH_002, "Permission denied"),
                status=403
            )

        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        role_ids = request.data.get('role_ids', [])

        if not username or not password:
            return Response(
                create_error_response(ErrorCode.VAL_001, "Username and password required"),
                status=400
            )

        if User.objects.filter(username=username).exists():
            return Response(
                create_error_response(ErrorCode.VAL_003, "Username already exists"),
                status=400
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        from security.models import Role
        for role_id in role_ids:
            try:
                role = Role.objects.get(id=role_id)
                from security.models import UserRole
                UserRole.objects.create(user=user, role=role, assigned_by=request.user)
            except Role.DoesNotExist:
                pass

        AuditLog.objects.create(
            action='CREATE',
            user=request.user,
            username=request.user.username,
            model_name='User',
            object_id=str(user.id),
            object_repr=user.username,
            change_message=f"Created user: {username}"
        )

        return Response(APIResponse.success(
            data={
                'id': str(user.id),
                'username': user.username,
                'email': user.email
            },
            message="User created successfully"
        ), status=201)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([RoleBasedPermission])
def users_detail(request, user_id):
    """Get, update, or delete a user."""
    from django.contrib.auth.models import User
    from security.models import UserRole

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            create_error_response(ErrorCode.AUTH_005, "User not found"),
            status=404
        )

    if request.method == 'GET':
        roles = list(user.user_roles.select_related('role').values('id', 'role__name'))

        return Response(APIResponse.success(
            data={
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'roles': [{'id': r['id'], 'name': r['role__name']} for r in roles]
            }
        ))

    elif request.method == 'PUT':
        if not request.user.is_superuser:
            return Response(
                create_error_response(ErrorCode.AUTH_002, "Permission denied"),
                status=403
            )

        user.email = request.data.get('email', user.email)
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.is_active = request.data.get('is_active', user.is_active)

        new_password = request.data.get('password')
        if new_password:
            user.set_password(new_password)

        user.save()

        role_ids = request.data.get('role_ids')
        if role_ids is not None:
            user.user_roles.all().delete()
            from security.models import Role
            for role_id in role_ids:
                try:
                    role = Role.objects.get(id=role_id)
                    UserRole.objects.create(user=user, role=role, assigned_by=request.user)
                except Role.DoesNotExist:
                    pass

        AuditLog.objects.create(
            action='UPDATE',
            user=request.user,
            username=request.user.username,
            model_name='User',
            object_id=str(user.id),
            object_repr=user.username,
            change_message=f"Updated user: {user.username}"
        )

        return Response(APIResponse.success(
            data={'id': str(user.id), 'username': user.username},
            message="User updated successfully"
        ))

    elif request.method == 'DELETE':
        if not request.user.is_superuser:
            return Response(
                create_error_response(ErrorCode.AUTH_002, "Permission denied"),
                status=403
            )

        if user == request.user:
            return Response(
                create_error_response(ErrorCode.AUTH_006, "Cannot delete yourself"),
                status=400
            )

        AuditLog.objects.create(
            action='DELETE',
            user=request.user,
            username=request.user.username,
            model_name='User',
            object_id=str(user.id),
            object_repr=user.username,
            change_message=f"Deleted user: {user.username}"
        )

        user.delete()
        return Response(APIResponse.success(data=None, message="User deleted successfully"))


@api_view(['GET', 'POST'])
@permission_classes([RoleBasedPermission])
def roles_list(request):
    """List or create roles."""
    from security.models import Role

    if request.method == 'GET':
        if not request.user.is_superuser:
            return Response(
                create_error_response(ErrorCode.AUTH_002, "Permission denied"),
                status=403
            )

        roles = Role.objects.all().order_by('name')
        return Response(APIResponse.success(
            data=[
                {
                    'id': str(r.id),
                    'name': r.name,
                    'description': r.description,
                    'is_active': r.is_active,
                    'permission_count': r.role_permissions.count(),
                    'user_count': r.role_users.count()
                }
                for r in roles
            ]
        ))

    elif request.method == 'POST':
        if not request.user.is_superuser:
            return Response(
                create_error_response(ErrorCode.AUTH_002, "Permission denied"),
                status=403
            )

        name = request.data.get('name')
        description = request.data.get('description', '')

        if not name:
            return Response(
                create_error_response(ErrorCode.VAL_001, "Role name required"),
                status=400
            )

        if Role.objects.filter(name=name).exists():
            return Response(
                create_error_response(ErrorCode.VAL_003, "Role already exists"),
                status=400
            )

        role = Role.objects.create(name=name, description=description)

        return Response(APIResponse.success(
            data={'id': str(role.id), 'name': role.name},
            message="Role created successfully"
        ), status=201)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([RoleBasedPermission])
def roles_detail(request, role_id):
    """Get, update, or delete a role."""
    from security.models import Role, Permission, RolePermission

    try:
        role = Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return Response(
            create_error_response("SEC_001", "Role not found"),
            status=404
        )

    if request.method == 'GET':
        permissions = role.role_permissions.select_related('permission').all()
        return Response(APIResponse.success(
            data={
                'id': str(role.id),
                'name': role.name,
                'description': role.description,
                'is_active': role.is_active,
                'permissions': [
                    {
                        'id': str(p.permission.id),
                        'name': p.permission.name,
                        'codename': p.permission.codename,
                        'module': p.permission.module
                    }
                    for p in permissions
                ],
                'user_count': role.role_users.count()
            }
        ))

    elif request.method == 'PUT':
        if not request.user.is_superuser:
            return Response(
                create_error_response(ErrorCode.AUTH_002, "Permission denied"),
                status=403
            )

        role.name = request.data.get('name', role.name)
        role.description = request.data.get('description', role.description)
        role.is_active = request.data.get('is_active', role.is_active)
        role.save()

        permission_ids = request.data.get('permission_ids')
        if permission_ids is not None:
            role.role_permissions.all().delete()
            for perm_id in permission_ids:
                try:
                    perm = Permission.objects.get(id=perm_id)
                    RolePermission.objects.create(role=role, permission=perm, granted_by=request.user)
                except Permission.DoesNotExist:
                    pass

        return Response(APIResponse.success(
            data={'id': str(role.id), 'name': role.name},
            message="Role updated successfully"
        ))

    elif request.method == 'DELETE':
        if not request.user.is_superuser:
            return Response(
                create_error_response(ErrorCode.AUTH_002, "Permission denied"),
                status=403
            )

        if role.role_users.exists():
            return Response(
                create_error_response("SEC_002", "Cannot delete role with assigned users"),
                status=400
            )

        role.delete()
        return Response(APIResponse.success(data=None, message="Role deleted successfully"))


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def permissions_list(request):
    """List all permissions."""
    if not request.user.is_superuser:
        return Response(
            create_error_response(ErrorCode.AUTH_002, "Permission denied"),
            status=403
        )

    from security.models import Permission

    permissions = Permission.objects.filter(is_active=True).order_by('module', 'codename')

    modules = request.query_params.get('modules')
    if modules:
        module_list = [m.strip() for m in modules.split(',')]
        permissions = permissions.filter(module__in=module_list)

    return Response(APIResponse.success(
        data=[
            {
                'id': str(p.id),
                'name': p.name,
                'codename': p.codename,
                'module': p.module,
                'description': p.description
            }
            for p in permissions
        ]
    ))


# ── Password Reset Endpoints (Offline: Admin-initiated) ──

@api_view(['POST'])
@permission_classes([RoleBasedPermission])
def admin_reset_password(request, user_id):
    """Admin resets a user's password. Returns temporary password."""
    from security.password_reset_service import PasswordResetService
    from django.contrib.auth.models import User

    if not request.user.is_authenticated:
        return Response(
            create_error_response(ErrorCode.AUTH_003, "Authentication required"),
            status=401
        )
    if not request.user.is_superuser:
        return Response(
            create_error_response(ErrorCode.AUTH_002, "Admin access required"),
            status=403
        )

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            create_error_response(ErrorCode.AUTH_005, "User not found"),
            status=404
        )

    result = PasswordResetService.admin_reset(request.user, target_user)
    if result["success"]:
        return Response(APIResponse.success(
            data={
                "username": target_user.username,
                "temporary_password": result["temporary_password"],
            },
            message=result["message"]
        ))
    return Response(
        create_error_response(ErrorCode.AUTH_002, result["message"]),
        status=403
    )


@api_view(['POST'])
def change_password(request):
    """User changes their own password."""
    from django.contrib.auth.password_validation import validate_password
    from security.password_reset_service import PasswordResetService

    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not old_password or not new_password:
        return Response(
            create_error_response(ErrorCode.VAL_001, "Old password and new password are required"),
            status=400
        )

    if not request.user.check_password(old_password):
        return Response(
            create_error_response(ErrorCode.AUTH_001, "Invalid old password"),
            status=400
        )

    result = PasswordResetService.force_change_password(request.user, new_password)
    if result["success"]:
        return Response(APIResponse.success(data=None, message=result["message"]))
    return Response(
        create_error_response(ErrorCode.VAL_002, result["message"]),
        status=400
    )


# ── TOTP / 2FA Endpoints ──

@api_view(['POST'])
@permission_classes([RoleBasedPermission])
def totp_setup(request):
    """Generate TOTP secret and QR code for current user."""
    from security.totp_service import TOTPService
    if not request.user.is_authenticated:
        return Response(
            create_error_response(ErrorCode.AUTH_003, "Authentication required"),
            status=401
        )
    result = TOTPService.generate_secret(request.user)
    return Response(APIResponse.success(
        data={
            "secret": result["secret"],
            "provisioning_uri": result["provisioning_uri"],
            "qr_code_base64": result["qr_code_base64"],
        },
        message="TOTP setup initiated. Verify with a code to confirm."
    ))


@api_view(['POST'])
@permission_classes([RoleBasedPermission])
def totp_verify(request):
    """Verify a TOTP code to confirm setup or authenticate."""
    from security.totp_service import TOTPService
    if not request.user.is_authenticated:
        return Response(
            create_error_response(ErrorCode.AUTH_003, "Authentication required"),
            status=401
        )
    code = request.data.get('code')
    if not code:
        return Response(
            create_error_response(ErrorCode.VAL_001, "TOTP code is required"),
            status=400
        )
    if TOTPService.verify_code(request.user, code):
        return Response(APIResponse.success(
            data={"confirmed": True},
            message="TOTP verified successfully. 2FA is now enabled."
        ))
    return Response(
        create_error_response(ErrorCode.AUTH_001, "Invalid TOTP code"),
        status=400
    )


@api_view(['POST'])
@permission_classes([RoleBasedPermission])
def totp_disable(request):
    """Disable TOTP 2FA for current user."""
    from security.totp_service import TOTPService
    if not request.user.is_authenticated:
        return Response(
            create_error_response(ErrorCode.AUTH_003, "Authentication required"),
            status=401
        )
    TOTPService.disable(request.user)
    return Response(APIResponse.success(
        data=None,
        message="TOTP 2FA has been disabled."
    ))


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def totp_status(request):
    """Get TOTP 2FA status for current user."""
    from security.totp_service import TOTPService
    if not request.user.is_authenticated:
        return Response(
            create_error_response(ErrorCode.AUTH_003, "Authentication required"),
            status=401
        )
    return Response(APIResponse.success(
        data={
            "enabled": TOTPService.is_enabled(request.user),
            "requires_2fa": TOTPService.requires_2fa(request.user),
        }
    ))

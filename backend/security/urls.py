"""Security app URL configuration - authentication endpoints."""
from django.urls import path
from security.views import (
    login_view, logout_view, user_profile, change_password,
    notifications_list, notifications_mark_read, notifications_unread_count,
    users_list, users_detail, roles_list, roles_detail, permissions_list,
    refresh_token_view,
    admin_reset_password,
    totp_setup, totp_verify, totp_disable, totp_status,
    password_reset_request, password_reset_confirm,
)

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('token/refresh/', refresh_token_view, name='token-refresh'),
    path('profile/', user_profile, name='profile'),
    path('change-password/', change_password, name='change-password'),
    path('notifications/', notifications_list, name='notifications-list'),
    path('notifications/read/', notifications_mark_read, name='notifications-mark-read'),
    path('notifications/unread-count/', notifications_unread_count, name='notifications-unread-count'),
    path('users/', users_list, name='users-list'),
    path('users/<uuid:user_id>/', users_detail, name='users-detail'),
    path('roles/', roles_list, name='roles-list'),
    path('roles/<int:role_id>/', roles_detail, name='roles-detail'),
    path('permissions/', permissions_list, name='permissions-list'),
    # Password reset (offline: admin-initiated)
    path('users/<uuid:user_id>/reset-password/', admin_reset_password, name='admin-reset-password'),
    # Email-based self-service password reset
    path('password-reset/request/', password_reset_request, name='password-reset-request'),
    path('password-reset/confirm/', password_reset_confirm, name='password-reset-confirm'),
    # TOTP / 2FA
    path('totp/setup/', totp_setup, name='totp-setup'),
    path('totp/verify/', totp_verify, name='totp-verify'),
    path('totp/disable/', totp_disable, name='totp-disable'),
    path('totp/status/', totp_status, name='totp-status'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('info/', views.LicenseInfoView.as_view(), name='license_info'),
    path('validate/', views.LicenseValidateView.as_view(), name='license_validate'),
    path('create/', views.LicenseCreateView.as_view(), name='license_create'),
    path('activation-request/', views.LicenseActivationRequestView.as_view(),
         name='license_activation_request'),
    path('import-license/', views.LicenseImportView.as_view(),
         name='license_import'),
    path('status/', views.LicenseStatusView.as_view(), name='license_status'),
]

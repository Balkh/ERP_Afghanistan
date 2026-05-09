from django.urls import path
from . import views

urlpatterns = [
    path('info/', views.license_info, name='license_info'),
    path('validate/', views.license_validate, name='license_validate'),
    path('create/', views.license_create, name='license_create'),
]

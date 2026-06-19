@echo off
REM =====================================================
REM Pharmacy ERP Build Script - PyInstaller Packaging
REM =====================================================
echo Building Pharmacy ERP Executable...

REM Clean previous builds
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "PharmacyERP.spec" del "PharmacyERP.spec"

REM Build using PyInstaller
pyinstaller --name "PharmacyERP" ^
    --onedir ^
    --windowed ^
    --icon=frontend\static\icon.ico ^
    --add-data "backend;backend" ^
    --add-data "frontend\api;frontend\api" ^
    --add-data "frontend\license;frontend\license" ^
    --add-data "frontend\security;frontend\security" ^
    --add-data "frontend\theme;frontend\theme" ^
    --add-data "frontend\ui;frontend\ui" ^
    --add-data "frontend\utils;frontend\utils" ^
    --add-data "backend\templates;backend\templates" ^
    --add-data "backend\static;backend\static" ^
    --hidden-import django ^
    --hidden-import django.core.handlers.wsgi ^
    --hidden-import rest_framework ^
    --hidden-import corsheaders ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    frontend\main.py

echo.
echo Build completed!
echo Executable location: dist\PharmacyERP\PharmacyERP.exe
echo.
pause
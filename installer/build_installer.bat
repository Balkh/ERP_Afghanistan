@echo off
REM =====================================================
REM Pharmacy ERP Windows Installer Build Script
REM Requires NSIS (Nullsoft Scriptable Install System)
REM =====================================================

echo ============================================
echo Pharmacy ERP Installer Builder
echo ============================================
echo.

REM Check if NSIS is installed
set MAKENSIS=
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    set MAKENSIS="C:\Program Files (x86)\NSIS\makensis.exe"
) else if exist "C:\Program Files\NSIS\makensis.exe" (
    set MAKENSIS="C:\Program Files\NSIS\makensis.exe"
) else (
    echo ERROR: NSIS not found!
    echo Please download and install NSIS from: http://nsis.sourceforge.net/Download
    echo.
    pause
    exit /b 1
)

echo Found NSIS: %MAKENSIS%
echo.

REM Check if build directory exists
if not exist "dist\PharmacyERP" (
    echo ERROR: Build directory not found!
    echo Please run build_exe.py first to create the executable.
    echo.
    pause
    exit /b 1
)

echo Build directory found. Creating installer...
echo.

REM Compile NSIS script
%MAKENSIS% installer\pharmacy_erp.nsi

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo Installer created successfully!
    echo ============================================
    echo.
    echo Output: PharmacyERP-Setup-1.0.0.exe
    echo.
) else (
    echo.
    echo ERROR: Failed to create installer!
    echo Check the NSIS script for errors.
    echo.
)

pause
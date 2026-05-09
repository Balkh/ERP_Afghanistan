; Pharmacy ERP Windows Installer Script (NSIS)
; This script creates a Windows installer for Pharmacy ERP

!include "MUI2.nsh"
!include "FileFunc.nsh"

; Application Information
!define APP_NAME "Pharmacy ERP"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Pharmacy ERP Solutions"
!define APP_URL "https://pharmacyerp.example.com"
!define APP_EXECUTABLE "PharmacyERP.exe"

; Output Settings
OutFile "PharmacyERP-Setup-${APP_VERSION}.exe"
InstallDir "$PROGRAMFILES64\PharmacyERP"
InstallDirRegKey HKLM "Software\${APP_NAME}" ""

; Request application privileges
RequestExecutionLevel admin

; Modern UI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${NSISDIR}\Docs\Modern UI\License.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; Installer Attributes
Name "${APP_NAME} ${APP_VERSION}"
BrandingText "${APP_NAME} - Enterprise Pharmacy Management System"
ShowInstDetails show
ShowUnInstDetails show

Section "Install ${APP_NAME}" SecInstall
    SectionIn RO

    ; Set output path to install directory
    SetOutPath "$INSTDIR"

    ; Install application files
    File /r "dist\PharmacyERP\*.*"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Create registry entries
    WriteRegStr HKLM "Software\${APP_NAME}" "" "$INSTDIR"
    WriteRegStr HKLM "Software\${APP_NAME}" "Version" "${APP_VERSION}"
    WriteRegStr HKLM "Software\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\${APP_NAME}" "URL" "${APP_URL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayIcon" "$\"$INSTDIR\${APP_EXECUTABLE}$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "Publisher" "${APP_PUBLISHER}"

    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXECUTABLE}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXECUTABLE}"

    ; Create data directories
    CreateDirectory "$APPDATA\${APP_NAME}"
    CreateDirectory "$APPDATA\${APP_NAME}\data"
    CreateDirectory "$APPDATA\${APP_NAME}\logs"
    CreateDirectory "$APPDATA\${APP_NAME}\config"
    CreateDirectory "$APPDATA\${APP_NAME}\backups"

    ; Set first-run flag
    WriteRegDWORD HKLM "Software\${APP_NAME}" "FirstRun" 1

    ; Display installation size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    DetailPrint "Installed size: $0 KB"
SectionEnd

Section "Create Desktop Shortcut" SecDesktop
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXECUTABLE}"
SectionEnd

Section "Add to PATH" SecPath
    ; Add application directory to system PATH (optional)
    ; This is typically not needed for GUI applications
    ; Uncomment if needed
    ; Push "$INSTDIR"
    ; Call AddToPath
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKLM "Software\${APP_NAME}"

    ; Remove shortcuts
    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\*.*"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    ; Remove installed files
    RMDir /r "$INSTDIR"

    ; Note: User data in %APPDATA% is preserved during uninstall
    ; This includes the database, logs, and backups

    ; Optional: Ask user if they want to remove user data
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "Do you want to remove all user data (database, logs, backups)?$\n$\nWARNING: This will permanently delete all your data!" \
        /SD IDNO IDNO KeepData
        RMDir /r "$APPDATA\${APP_NAME}"
    KeepData:
SectionEnd
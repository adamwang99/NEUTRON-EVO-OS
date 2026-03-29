@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   Apply NEUTRON EVO OS to this project
echo ========================================
echo.

REM Get current directory
set "PROJECT_DIR=%CD%"

REM Copy CLAUDE.md to current directory
echo [1/1] Copying CLAUDE.md to project...
copy /Y "%~dp0CLAUDE.md" "%PROJECT_DIR%\CLAUDE.md" >nul

if %errorlevel% equ 0 (
    echo.
    echo    SUCCESS! CLAUDE.md has been copied.
    echo    Claude Sonnet will now read context automatically.
    echo.
    echo    Project: %PROJECT_DIR%
    echo.
) else (
    echo.
    echo    ERROR: Failed to copy CLAUDE.md
    echo.
)

pause

@echo off
echo ===================================
echo SiteShare - Website Sharing Tool
echo ===================================
echo.
echo Choose an option:
echo 1. Start in normal mode (static files only)
echo 2. Start with PHP support (requires MAMP/XAMPP)
echo.

set /p option="Enter option (1 or 2): "

if "%option%"=="1" (
    echo.
    echo Starting SiteShare in normal mode...
    echo.
    python share_website.py
) else if "%option%"=="2" (
    echo.
    echo Starting SiteShare with PHP support...
    echo.
    python share_website.py --php
) else (
    echo.
    echo Invalid option. Starting in normal mode...
    echo.
    python share_website.py
)

echo.
echo Press any key to exit...
pause > nul

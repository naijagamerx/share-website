# SiteShare Installer for Windows
# This script downloads and runs SiteShare directly from GitHub

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  SiteShare - Website Sharing Tool" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installing SiteShare..." -ForegroundColor Yellow

# Create a temporary directory
$tempDir = Join-Path $env:TEMP "SiteShare"
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Define the GitHub repository
$repo = "naijagamerx/share-website"
$branch = "main"

# Download the main script
Write-Host "Downloading share_website.py..." -ForegroundColor Yellow
$scriptUrl = "https://raw.githubusercontent.com/$repo/$branch/share_website.py"
Invoke-WebRequest -Uri $scriptUrl -OutFile (Join-Path $tempDir "share_website.py")

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Change to the temporary directory
Set-Location -Path $tempDir

# Run the script
Write-Host ""
Write-Host "Starting SiteShare..." -ForegroundColor Green
Write-Host ""
try {
    python share_website.py
} catch {
    Write-Host "Error running SiteShare: $_" -ForegroundColor Red
}

# Cleanup
Write-Host ""
Write-Host "SiteShare session ended." -ForegroundColor Yellow
Write-Host ""
Write-Host "To install SiteShare permanently:" -ForegroundColor Cyan
Write-Host "1. Visit: https://github.com/$repo" -ForegroundColor Cyan
Write-Host "2. Click 'Code' and 'Download ZIP'" -ForegroundColor Cyan
Write-Host "3. Extract the ZIP file to a location of your choice" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

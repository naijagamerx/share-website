#!/bin/bash
# SiteShare Installer for Mac/Linux
# This script downloads and runs SiteShare directly from GitHub

echo "======================================="
echo "  SiteShare - Website Sharing Tool"
echo "======================================="
echo ""
echo "Installing SiteShare..."

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR" || exit 1

# Define the GitHub repository
REPO="naijagamerx/share-website"
BRANCH="main"

# Download the main script
echo "Downloading share_website.py..."
curl -s -o share_website.py "https://raw.githubusercontent.com/$REPO/$BRANCH/share_website.py"

# Check if Python is installed
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
    echo "Found Python: $($PYTHON_CMD --version)"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
    echo "Found Python: $($PYTHON_CMD --version)"
else
    echo "Python is not installed."
    echo "Please install Python 3 using your package manager or from https://www.python.org/downloads/"
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

# Make the script executable
chmod +x share_website.py

# Run the script
echo ""
echo "Starting SiteShare..."
echo ""
$PYTHON_CMD share_website.py

# Cleanup
echo ""
echo "SiteShare session ended."
echo ""
echo "To install SiteShare permanently:"
echo "1. Visit: https://github.com/$REPO"
echo "2. Click 'Code' and 'Download ZIP'"
echo "3. Extract the ZIP file to a location of your choice"
echo ""
echo "Press Enter to exit..."
read -r

# Clean up the temporary directory
rm -rf "$TEMP_DIR"

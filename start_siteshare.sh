#!/bin/bash
echo "==================================="
echo "SiteShare - Website Sharing Tool"
echo "==================================="
echo ""
echo "Choose an option:"
echo "1. Start in normal mode (static files only)"
echo "2. Start with PHP support (requires MAMP/XAMPP)"
echo ""

read -p "Enter option (1 or 2): " option

if [ "$option" = "1" ]; then
    echo ""
    echo "Starting SiteShare in normal mode..."
    echo ""
    python3 share_website.py
elif [ "$option" = "2" ]; then
    echo ""
    echo "Starting SiteShare with PHP support..."
    echo ""
    python3 share_website.py --php
else
    echo ""
    echo "Invalid option. Starting in normal mode..."
    echo ""
    python3 share_website.py
fi

echo ""
echo "Press Enter to exit..."
read

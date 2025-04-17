#!/usr/bin/env python3
"""
Simple example of using SiteShare programmatically.

This script demonstrates how to use the SiteShare functions
in your own Python code.
"""

import sys
import os

# Add the parent directory to the path so we can import share_website
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from share_website import get_local_ip, run_server

def main():
    """Run a simple example of SiteShare."""
    # Get the local IP address
    ip = get_local_ip()
    print(f"Your local IP address is: {ip}")
    
    # Define the directory to serve (current directory in this example)
    directory = "."
    
    # Define the port to serve on
    port = 8080
    
    print(f"Starting server to share '{os.path.abspath(directory)}' on port {port}")
    print("Press Ctrl+C to stop the server")
    
    # Start the server
    run_server(directory=directory, port=port)

if __name__ == "__main__":
    main()

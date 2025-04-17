#!/usr/bin/env python3
"""
SiteShare - A simple tool to share local websites across your network.

This script allows you to easily share a local directory (like a website) with other
devices on your local network. It automatically detects your local IP address and
starts a web server that makes the directory accessible to all devices on the network.

It's particularly useful for web developers who need to test their sites on multiple
devices, or for quickly sharing files between computers on the same network.

Author: SiteShare Team
License: MIT
Repository: https://github.com/naijagamerx/share-website
"""

import http.server
import socket
import argparse
import os
import sys
import errno  # Import errno for cross-platform error codes
import platform
import urllib.request
import urllib.error
import urllib.parse
import shutil
import re
import subprocess
from http import HTTPStatus
import time # For potential future use, like delays

# --- Configuration ---
VERSION = "1.0.0"  # SiteShare version
AUTHOR = "SiteShare Team (Modified by demohomex.com)"
GITHUB_REPO = "https://github.com/naijagamerx/share-website"
DESIGNED_BY = "demohomex.com"

# Define paths for different web servers and platforms
WEB_SERVER_PATHS = {
    "windows": [
        "c:/MAMP/htdocs/",      # MAMP on Windows
        "c:/xampp/htdocs/",     # XAMPP on Windows
        "c:/wamp/www/",         # WAMP on Windows
        "c:/wamp64/www/"        # WAMP64 on Windows
    ],
    "darwin": [                # macOS
        "/Applications/MAMP/htdocs/",
        "/opt/lampp/htdocs/"   # XAMPP on macOS
    ],
    "linux": [
        "/opt/lampp/htdocs/",  # XAMPP on Linux
        "/var/www/html/"       # Default Apache on Linux
    ]
}

# Common PHP server ports to check
PHP_SERVER_PORTS = [80, 8888, 8080, 8000]

# Function to check if a local PHP server is running
def find_php_server():
    """
    Detect if a PHP server (like MAMP or XAMPP) is running locally.
    Returns the port number if found, otherwise None.
    """
    for port in PHP_SERVER_PORTS:
        try:
            # Try to connect to localhost on the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)  # Short timeout
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:  # Port is open
                    # Try to fetch the server header to confirm it's a web server
                    try:
                        response = urllib.request.urlopen(f"http://localhost:{port}", timeout=1)
                        server = response.info().get('Server', '')
                        if 'apache' in server.lower() or 'php' in server.lower() or 'nginx' in server.lower():
                            # Message is now printed in run_server after confirmation
                            return port # Return port, message handled later
                    except Exception:
                        pass  # Not a web server or couldn't connect
        except Exception:
            pass  # Couldn't check this port

    # Message printed in run_server if needed
    return None

# --- ANSI Color Codes ---
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN = "\033[96m"
C_WHITE = "\033[97m"
C_BR_WHITE = "\033[1;97m" # Bright White

# Simple check for color support (basic)
def supports_color():
    """Check if the terminal likely supports color."""
    # Check for common CI environments where color might be forced off
    if os.environ.get('CI') or os.environ.get('TF_BUILD') or os.environ.get('GITHUB_ACTIONS'):
        return False
    # Check if running in a standard terminal
    is_a_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    if sys.platform == "win32":
        # On Windows, check if WT_SESSION is set (Windows Terminal) or ConEmuANSI is ON
        # Basic cmd.exe might not support without extra steps (like calling os.system(''))
        return is_a_tty and (os.environ.get('WT_SESSION') is not None or os.environ.get('ConEmuANSI') == 'ON')
    # For other OS (Linux, macOS), check TERM and isatty
    term = os.environ.get('TERM', 'dumb')
    return is_a_tty and term != 'dumb'

# Enable colors only if supported
if not supports_color():
    C_RESET = C_BOLD = C_DIM = C_RED = C_GREEN = C_YELLOW = C_BLUE = C_MAGENTA = C_CYAN = C_WHITE = C_BR_WHITE = ""

# --- Helper Functions ---

def print_separator(char="─", length=60, color=C_DIM):
    """Prints a separator line."""
    print(f"{color}{char * length}{C_RESET}")

def get_local_ip() -> str:
    """
    Detect the local IP address of the machine.

    This function attempts multiple methods to determine the local IP address
    that would be used to connect to external hosts. It has fallback mechanisms
    in case the primary method fails.

    Returns:
        str: The detected local IP address (e.g., '192.168.1.100')
              or '127.0.0.1' if detection fails
    """
    s = None  # Initialize socket to None
    try:
        # Primary method: Create a temporary socket to get the IP address
        # that would be used to connect to an external host
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't actually send data, just establishes a potential connection route
        s.connect(("8.8.8.8", 80))  # Google's public DNS server
        local_ip = s.getsockname()[0]
    except OSError:  # Handle cases where the network might be down or host unreachable
        try:
            # Fallback 1: Get IP associated with the hostname
            local_ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            # Fallback 2: If hostname resolution fails, use loopback
            local_ip = "127.0.0.1"
    finally:
        if s:
            s.close()
    return local_ip

class PHPProxyHandler(http.server.BaseHTTPRequestHandler):
    """
    Handler that proxies requests to a local PHP server.
    """
    php_server_port = None
    directory = None
    script_dir = None

    def do_GET(self):
        return self.proxy_request('GET')

    def do_POST(self):
        return self.proxy_request('POST')

    def do_HEAD(self):
        return self.proxy_request('HEAD')

    def proxy_request(self, method):
        # Special endpoint to get server information
        if self.path == '/siteshare-info.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            info = {
                'directory': os.path.abspath(self.directory),
                'version': VERSION,
                'mode': 'PHP Proxy',
                'php_port': self.php_server_port
            }
            self.wfile.write(bytes(str(info).replace("'", '"'), 'utf-8'))
            return

        # For root requests, we'll let the PHP server handle it directly
        # If the PHP server returns 404, we'll show the welcome page (handled in error section)

        # Security check: Ensure the request is within the shared directory
        # Get the base directory name from the full path
        base_dir_name = os.path.basename(os.path.normpath(self.directory))

        # Check if the path starts with the base directory or is at the root
        if self.path == '/':
            # For root path, redirect to the shared directory
            self.send_response(302)  # Found/Redirect
            self.send_header('Location', f'/{base_dir_name}/')
            self.end_headers()
            return
        elif not (self.path.startswith(f'/{base_dir_name}/') or self.path == f'/{base_dir_name}'):
            print(f"Security block: Attempted access to {self.path} outside of shared directory {base_dir_name}")
            self.send_response(403)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>403 Forbidden</h1><p>Access is restricted to the shared directory.</p></body></html>")
            return

        # Forward the request to the PHP server (using localhost is most reliable for local proxying)
        # For paths that include the base directory name, we need to strip it when forwarding to PHP server
        base_dir_name = os.path.basename(os.path.normpath(self.directory))
        php_path = self.path

        # If the path starts with the base directory name, strip it to access the correct files
        if self.path.startswith(f'/{base_dir_name}/') or self.path == f'/{base_dir_name}':
            # Remove the base directory name from the path
            php_path = self.path[len(f'/{base_dir_name}'):]
            # If the resulting path is empty, use root
            if not php_path:
                php_path = '/'
            print(f"Remapped path from {self.path} to {php_path} for PHP server")

        target_url = f"http://localhost:{self.php_server_port}{php_path}"

        # Special handling for PHP files - add query string to force PHP processing
        if self.path.endswith('.php') and '?' not in self.path:
            target_url += '?siteshare=1'  # Add a dummy parameter to ensure PHP processing

        # Only print debug info for PHP files or errors
        if self.path.endswith('.php'):
            print(f"Proxying {method} request for {self.path} to {target_url}") # Debug

        try:
            # Create a request to the PHP server
            headers = {key: value for key, value in self.headers.items()}

            # Add special headers to help with PHP processing
            if self.path.endswith('.php'):
                headers['X-Requested-With'] = 'XMLHttpRequest'
                headers['Accept'] = 'text/html,application/xhtml+xml,application/xml'

            # Read the request body for POST requests
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            # Create the request
            req = urllib.request.Request(
                target_url,
                data=body,
                headers=headers,
                method=method
            )

            # Send the request to the PHP server
            if self.path.endswith('.php'):
                print(f"Sending request to PHP server: {target_url}") # Debug
            with urllib.request.urlopen(req) as response:
                # Copy the response status and headers
                self.send_response(response.status)
                if self.path.endswith('.php'):
                    print(f"PHP server responded with status: {response.status}") # Debug

                # Set content type based on file extension for PHP files
                content_type = None
                for header, value in response.getheaders():
                    if header.lower() == 'content-type':
                        content_type = value
                        if self.path.endswith('.php'):
                            print(f"Content-Type from PHP server: {value}") # Debug
                    if header.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(header, value)

                # If PHP file is requested but content-type is not set correctly, fix it
                if self.path.endswith('.php') and (not content_type or 'octet-stream' in content_type):
                    print(f"Fixing content type for PHP file") # Debug
                    self.send_header('Content-type', 'text/html')

                self.end_headers()

                # Copy the response body
                shutil.copyfileobj(response, self.wfile)

        except urllib.error.HTTPError as e:
            print(f"HTTP Error from PHP server: {e.code} {e.reason}") # Debug
            # If we get a 404 for the root path, try to show the welcome page
            if e.code == 404 and (self.path == '/' or self.path == '/index.html'):
                welcome_path = os.path.join(self.script_dir, 'welcome.html')
                if os.path.exists(welcome_path):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    with open(welcome_path, 'rb') as file:
                        self.wfile.write(file.read())
                    return

            # Otherwise, pass through the error
            self.send_response(e.code)
            for header, value in e.headers.items():
                if header.lower() not in ('transfer-encoding', 'connection'):
                    self.send_header(header, value)
            self.end_headers()
            if e.fp:
                shutil.copyfileobj(e.fp, self.wfile)

        except Exception as e:
            print(f"Exception in proxy request: {str(e)}") # Debug
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            error_message = f"<html><body><h1>Error</h1><p>Failed to proxy request: {str(e)}</p></body></html>"
            self.wfile.write(error_message.encode('utf-8'))

class SiteShareHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom request handler for SiteShare.

    This handler serves a welcome page if the root directory is accessed and
    provides information about the server via a special JSON endpoint.
    """
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        # Special endpoint to get server information
        if self.path == '/siteshare-info.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            info = {
                'directory': os.path.abspath(self.directory),
                'version': VERSION,
                'mode': 'Static Files'
            }
            self.wfile.write(bytes(str(info).replace("'", '"'), 'utf-8'))
            return

        # Security check: For root directory sharing, allow all paths
        # For specific directory sharing, restrict to that directory
        if self.directory != '.' and self.directory != './':
            # Get the base directory name from the full path
            base_dir_name = os.path.basename(os.path.normpath(self.directory))

            # If the path doesn't start with the base directory and isn't the root, block it
            if self.path == '/':
                # For root path, redirect to the shared directory
                self.send_response(302)  # Found/Redirect
                self.send_header('Location', f'/{base_dir_name}/')
                self.end_headers()
                return
            elif not (self.path.startswith(f'/{base_dir_name}/') or self.path == f'/{base_dir_name}'):
                print(f"Security block: Attempted access to {self.path} outside of shared directory {base_dir_name}")
                self.send_response(403)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<html><body><h1>403 Forbidden</h1><p>Access is restricted to the shared directory.</p></body></html>")
                return

            # For paths that include the base directory name, we need to modify the path
            # to correctly serve files from the actual directory
            if self.path.startswith(f'/{base_dir_name}/') or self.path == f'/{base_dir_name}':
                # Store the original path for later use
                original_path = self.path
                # Remove the base directory name from the path
                self.path = self.path[len(f'/{base_dir_name}'):]
                # If the resulting path is empty, use root
                if not self.path:
                    self.path = '/'
                print(f"Remapped path from {original_path} to {self.path} for static file serving")

        # Serve welcome page for specific paths
        # Note: Root path '/' is already handled above with redirection
        base_dir_name = os.path.basename(os.path.normpath(self.directory))
        if self.path == f'/{base_dir_name}/' or self.path == f'/{base_dir_name}':
            has_index = False
            for index_file in ['index.html', 'index.htm', 'index.php', 'default.html', 'default.htm', 'default.php']:
                if os.path.exists(os.path.join(self.directory, index_file)):
                    has_index = True
                    break

            if not has_index:
                welcome_path = os.path.join(self.script_dir, 'welcome.html')
                if os.path.exists(welcome_path):
                    try:
                        with open(welcome_path, 'rb') as file:
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            self.wfile.write(file.read())
                        return # Served welcome page
                    except Exception as e:
                        self.log_error(f"Error serving welcome page: {e}")
                        # Fall through to default handler if error occurs

        # For all other requests (including root if index exists), use the standard behavior
        # The base handler uses the 'directory' passed in __init__
        super().do_GET()

def run_server(directory: str = ".", port: int = 8000, php_mode: bool = False) -> None:
    """
    Starts a simple HTTP server, handling port conflicts and permissions.

    This function changes to the specified directory and starts an HTTP server
    that makes the directory accessible over the network. It includes error handling
    for common issues like port conflicts and permission problems.

    Args:
        directory (str): The directory to serve (default: current directory)
        port (int): The port to serve on (default: 8000)
        php_mode (bool): Whether to enable PHP processing (default: False)

    Returns:
        None
    """
    abs_dir_initial = os.path.abspath(directory) # Get absolute path early for messages
    try:
        # Ensure the directory exists
        if not os.path.isdir(abs_dir_initial):
            print(f"{C_RED}Error: Directory not found: {C_BOLD}{abs_dir_initial}{C_RESET}")
            sys.exit(1)
    except OSError as e:
        print(f"{C_RED}Error accessing directory {C_BOLD}{abs_dir_initial}{C_RESET}{C_RED}: {e}{C_RESET}")
        sys.exit(1)

    # --- Determine Server Mode (Static vs PHP Proxy) ---
    php_server_port = None
    final_php_mode = False # Track if PHP mode is actually used

    if php_mode:
        print(f"{C_CYAN}PHP mode requested. Checking for local PHP server...{C_RESET}")
        php_server_port = find_php_server()
        if php_server_port:
            print(f"{C_GREEN}✓ Found PHP-capable server on port {C_BOLD}{php_server_port}{C_RESET}")
            final_php_mode = True
        else:
            print(f"{C_YELLOW}! No running PHP server detected on common ports ({', '.join(map(str, PHP_SERVER_PORTS))}).{C_RESET}")
            print(f"{C_YELLOW}  Make sure MAMP, XAMPP, or similar is running if you need PHP processing.{C_RESET}")
            print(f"{C_BLUE}  Falling back to static file serving mode.{C_RESET}")
            php_mode = False # Force static mode if server not found
    else:
         print(f"{C_BLUE}PHP mode not requested. Using static file serving mode.{C_RESET}")


    # --- Create the appropriate handler ---
    if final_php_mode and php_server_port:
        print(f"{C_GREEN}Using PHP proxy mode (forwarding to localhost:{php_server_port}).{C_RESET}")
        # Create a handler class with the PHP server port
        PHPProxyHandler.php_server_port = php_server_port
        PHPProxyHandler.directory = directory
        PHPProxyHandler.script_dir = os.path.dirname(os.path.abspath(__file__))
        handler = PHPProxyHandler
    else:
        # If PHP mode was requested but failed, this message is already shown
        if not php_mode: # Only print if PHP wasn't requested initially
             print(f"{C_GREEN}Using static file mode.{C_RESET}")
        # Use our custom static file handler, passing the target directory
        handler = lambda *args, **kwargs: SiteShareHandler(*args, directory=abs_dir_initial, **kwargs)

    # --- Start HTTP Server ---
    address = ("", port) # Bind to all interfaces
    max_retries = 3
    retries = 0

    while retries < max_retries:
        try:
            # Use ThreadingHTTPServer for better handling of multiple requests
            with http.server.ThreadingHTTPServer(address, handler) as httpd:
                local_ip = get_local_ip()
                # abs_dir = os.path.abspath(directory) # Already got abs_dir_initial

                print_separator("═", 60, C_BLUE)
                print(f"{C_GREEN}Server started successfully!{C_RESET}")
                print(f"{C_WHITE}Serving from: {C_BOLD}{abs_dir_initial}{C_RESET}")
                print(f"  {C_CYAN}Local:  {C_BOLD}http://localhost:{port}{C_RESET}")
                print(f"  {C_CYAN}Network:{C_BOLD} http://{local_ip}:{port}{C_RESET}")
                print_separator("-", 40, C_DIM)
                print(f"{C_YELLOW}Important Notes:{C_RESET}")
                print(f"{C_DIM}  - 'localhost' only works on this machine.{C_RESET}")
                print(f"{C_DIM}  - Other devices MUST use the Network IP ({local_ip}).{C_RESET}")
                print(f"{C_DIM}  - Ensure firewall allows connections on port {port}.{C_RESET}")
                print_separator("═", 60, C_BLUE)
                print(f"\n{C_MAGENTA}Press {C_BOLD}Ctrl+C{C_RESET}{C_MAGENTA} to stop the server.{C_RESET}")

                httpd.serve_forever() # Blocks here until interrupted

        except OSError as e:
            if e.errno in (errno.EADDRINUSE, 98, 48, 10048): # Address already in use
                retries += 1
                print(f"\n{C_RED}Error: Port {C_BOLD}{port}{C_RESET}{C_RED} is already in use.{C_RESET}")
                if retries < max_retries:
                    try:
                        prompt = (f"{C_YELLOW}Enter a different port (attempt {retries}/{max_retries-1}) "
                                  f"or press Enter to exit: {C_RESET}")
                        new_port_str = input(prompt)
                        if not new_port_str:
                            print(f"{C_BLUE}Exiting.{C_RESET}")
                            sys.exit(1)
                        new_port = int(new_port_str)
                        if 1 <= new_port <= 65535:
                            port = new_port
                            address = ("", port) # Update address tuple for next attempt
                            print(f"{C_BLUE}Retrying with port {C_BOLD}{port}{C_RESET}{C_BLUE}...{C_RESET}")
                        else:
                            print(f"{C_RED}Invalid port number. Must be between 1 and 65535.{C_RESET}")
                            retries -= 1 # Decrement because this wasn't a valid port attempt
                    except ValueError:
                        print(f"{C_RED}Invalid input. Please enter a number.{C_RESET}")
                        retries -= 1 # Decrement because this wasn't a valid port attempt
                else:
                    print(f"{C_RED}Maximum retry attempts reached. Exiting.{C_RESET}")
                    sys.exit(1) # Exit after max retries for port conflict
            elif e.errno in (errno.EACCES, 13): # Permission denied
                print(f"\n{C_RED}Error: Permission denied to use port {C_BOLD}{port}{C_RESET}{C_RED}.{C_RESET}")
                print(f"{C_YELLOW}Try a port number above 1024 or run with administrator/root privileges.{C_RESET}")
                sys.exit(1) # Exit immediately on permission error
            else:
                # Catch other potential OS errors during server start
                print(f"\n{C_BOLD}{C_RED}An unexpected OS error occurred: {e}{C_RESET}")
                sys.exit(1) # Exit on other OS errors

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print(f"\n{C_MAGENTA}Stopping the server...{C_RESET}")
            break # Exit the while loop

        except Exception as e:
            # Catch any other unexpected errors during server setup/run
            print(f"\n{C_BOLD}{C_RED}An unexpected error occurred: {e}{C_RESET}")
            sys.exit(1) # Exit on general errors

    # This part is reached if the loop finishes without starting (e.g., max retries exceeded)
    # However, sys.exit(1) is called within the loop for port conflicts now.
    # Keep it just in case, though it might be unreachable.
    if retries >= max_retries:
         print(f"{C_BOLD}{C_RED}Failed to start server after multiple attempts.{C_RESET}")

def print_banner():
    """Prints the application banner with ASCII art and metadata."""
    # Block ASCII art for "Site Share" with more stylized design
    banner_art = f"""
{C_CYAN}╔═══════════════════════════════════════════════════════════════════════╗{C_RESET}
{C_CYAN}║ ███████╗██╗████████╗███████╗    ███████╗██╗  ██╗ █████╗ ██████╗ ███████╗ ║{C_RESET}
{C_CYAN}║ ██╔════╝██║╚══██╔══╝██╔════╝    ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔════╝ ║{C_RESET}
{C_CYAN}║ ███████╗██║   ██║   █████╗      ███████╗███████║███████║██████╔╝█████╗   ║{C_RESET}
{C_CYAN}║ ╚════██║██║   ██║   ██╔══╝      ╚════██║██╔══██║██╔══██║██╔══██╗██╔══╝   ║{C_RESET}
{C_CYAN}║ ███████║██║   ██║   ███████╗    ███████║██║  ██║██║  ██║██║  ██║███████╗ ║{C_RESET}
{C_CYAN}║ ╚══════╝╚═╝   ╚═╝   ╚══════╝    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ║{C_RESET}
{C_CYAN}╚═══════════════════════════════════════════════════════════════════════╝{C_RESET}
    """
    print(banner_art)
    print(f"{C_MAGENTA}╔═════════════════════ {C_BOLD}Local Website Sharing Tool{C_RESET}{C_MAGENTA} ═════════════════════╗{C_RESET}")
    print(f"{C_MAGENTA}║{C_RESET} {C_WHITE}Version: {C_BOLD}{VERSION}{C_RESET}                                                {C_MAGENTA}║{C_RESET}")
    print(f"{C_MAGENTA}║{C_RESET} {C_WHITE}Author: {C_BOLD}{AUTHOR}{C_RESET}                                          {C_MAGENTA}║{C_RESET}")
    print(f"{C_MAGENTA}║{C_RESET} {C_WHITE}Designed by: {C_BOLD}{DESIGNED_BY}{C_RESET}                                {C_MAGENTA}║{C_RESET}")
    print(f"{C_MAGENTA}║{C_RESET} {C_WHITE}GitHub: {C_DIM}{GITHUB_REPO}{C_RESET}                {C_MAGENTA}║{C_RESET}")
    print(f"{C_MAGENTA}╚═══════════════════════════════════════════════════════════════════════╝{C_RESET}")
    print() # Add a blank line after the banner

def main():
    """
    Main entry point for the SiteShare application.

    This function handles command-line argument parsing, directory selection,
    and starting the server. It's designed to be called both as a script and
    as an entry point when installed as a package.

    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    # Print banner
    print_banner()

    # Setup command-line argument parsing with examples
    parser = argparse.ArgumentParser(
        description="Easily share a local website directory on your network.",
        epilog="Examples:\n"
               "  python share_website.py                   # Serve current directory on port 8000\n"
               "  python share_website.py --port 8080       # Serve current directory on port 8080\n"
               "  python share_website.py --dir ./public    # Serve './public' directory on port 8000\n"
               "  python share_website.py --php             # Enable PHP processing (requires MAMP/XAMPP)\n"
               "  python share_website.py --dir /var/www --port 80 # Serve '/var/www' on port 80 (might need sudo/admin)",
        formatter_class=argparse.RawDescriptionHelpFormatter # Keep epilog formatting
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number to serve the website on (default: 8000)."
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="[Optional] Specific directory to serve (overrides site selection)"
    )
    parser.add_argument(
        "--php",
        action="store_true",
        help="Enable PHP processing by proxying to a local PHP server (MAMP/XAMPP)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"SiteShare {VERSION}",
        help="Show the version number and exit"
    )
    args = parser.parse_args()

    # --- System Information ---
    print(f"{C_MAGENTA}System Info:{C_RESET}")
    print(f"  OS:     {C_WHITE}{platform.system()} {platform.release()}{C_RESET}")
    print(f"  Python: {C_WHITE}{platform.python_version()}{C_RESET}")
    print_separator()

    # --- Validate Port ---
    if not (1 <= args.port <= 65535):
        print(f"{C_RED}Error: Invalid port number {C_BOLD}{args.port}{C_RESET}{C_RED}. Must be between 1 and 65535.{C_RESET}")
        return 1

    # --- Determine Directory ---
    print(f"{C_MAGENTA}Directory Selection:{C_RESET}")
    target_dir = args.dir
    if not target_dir:
        # Get the appropriate web server paths for the current platform
        system = platform.system().lower()
        if system == "darwin":
            system = "darwin"  # macOS
        elif system == "windows":
            system = "windows"
        else:
            system = "linux"  # Default to Linux for other systems

        # Try to find websites in common web server directories
        all_sites = []
        found_paths = []

        for path in WEB_SERVER_PATHS.get(system, []):
            try:
                if os.path.isdir(path):
                    sites = [name for name in os.listdir(path)
                            if os.path.isdir(os.path.join(path, name))]
                    if sites:
                        all_sites.extend([(path, site) for site in sites])
                        found_paths.append(path)
            except (FileNotFoundError, PermissionError):
                pass

        if not all_sites:
            print(f"{C_YELLOW}! No websites found in common web server directories: {C_DIM}{', '.join(WEB_SERVER_PATHS.get(system, []))}{C_RESET}")
            print(f"{C_YELLOW}  Please specify a directory using the {C_BOLD}--dir{C_RESET}{C_YELLOW} option.{C_RESET}")
            return 1

        print(f"{C_CYAN}Available websites found:{C_RESET}")
        for i, (path, site) in enumerate(all_sites, 1):
            print(f"  {C_GREEN}{i}{C_RESET}. {C_BOLD}{site}{C_RESET} {C_DIM}(in {path}){C_RESET}")

        selection = input(f"\n{C_YELLOW}Enter site number to share (or 'x' to cancel): {C_RESET}").strip()
        if selection.lower() == 'x':
            print(f"{C_BLUE}Operation cancelled by user.{C_RESET}")
            return 0

        try:
            selected_idx = int(selection) - 1
            path, site = all_sites[selected_idx]
            target_dir = os.path.join(path, site)
            print(f"{C_GREEN}✓ Selected: {C_BOLD}{site}{C_RESET}")
        except (ValueError, IndexError):
            print(f"{C_RED}Error: Invalid selection.{C_RESET}")
            return 1
    else:
        # Use explicitly specified directory
        target_dir = os.path.abspath(target_dir)
        print(f"{C_CYAN}Using specified directory: {C_BOLD}{target_dir}{C_RESET}")

    print_separator()

    # --- Security Warning ---
    print(f"{C_BOLD}{C_YELLOW}############################################{C_RESET}")
    print(f"{C_BOLD}{C_YELLOW}#          WARNING: NETWORK EXPOSURE         #{C_RESET}")
    print(f"{C_BOLD}{C_YELLOW}############################################{C_RESET}")
    print(f"{C_YELLOW}# This script makes the directory:{C_RESET}")
    print(f"{C_YELLOW}#  '{C_BOLD}{target_dir}{C_RESET}{C_YELLOW}'{C_RESET}")
    print(f"{C_YELLOW}# accessible to {C_BOLD}ALL{C_RESET}{C_YELLOW} devices on your local network.{C_RESET}")
    print(f"{C_YELLOW}#{C_RESET}")
    print(f"{C_YELLOW}# - Ensure you trust your network environment.{C_RESET}")
    print(f"{C_YELLOW}# - Do {C_BOLD}NOT{C_RESET}{C_YELLOW} serve directories containing sensitive data.{C_RESET}")
    print(f"{C_YELLOW}# - Stop the server ({C_BOLD}Ctrl+C{C_RESET}{C_YELLOW}) when finished.{C_RESET}")
    print(f"{C_BOLD}{C_YELLOW}############################################{C_RESET}\n")

    # --- Start Server ---
    print(f"{C_MAGENTA}Starting Server...{C_RESET}")
    try:
        run_server(directory=target_dir, port=args.port, php_mode=args.php)
        print(f"\n{C_BLUE}Server stopped gracefully.{C_RESET}")
        return 0
    except KeyboardInterrupt:
        # Already handled in run_server, but catch here too for clean exit
        print(f"\n{C_BLUE}Server stopped by user.{C_RESET}")
        return 0
    except SystemExit:
         # Allow sys.exit() calls within run_server to propagate
         pass
    except Exception as e:
        print(f"\n{C_BOLD}{C_RED}An unexpected error occurred in main: {e}{C_RESET}")
        return 1

if __name__ == "__main__":
    # Ensure clean exit on Ctrl+C before server starts
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{C_BLUE}Operation cancelled by user.{C_RESET}")
        sys.exit(1)

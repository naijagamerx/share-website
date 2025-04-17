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

# Configuration
VERSION = "1.0.0"  # SiteShare version

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
                            print(f"Found PHP-capable server on port {port} ({server})")
                            return port
                    except:
                        pass  # Not a web server or couldn't connect
        except:
            pass  # Couldn't check this port

    return None

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
        target_url = f"http://localhost:{self.php_server_port}{self.path}"

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
    try:
        # Ensure the directory exists before trying to change into it
        if not os.path.isdir(directory):
            print(f"Error: Directory not found: {directory}")
            sys.exit(1)
        # os.chdir(directory) # No longer needed, handler uses the directory argument
    except OSError as e:
        # This check might not be strictly necessary anymore without chdir, but keep for safety
        print(f"Error accessing directory {directory}: {e}")
        sys.exit(1)

    # Determine if we should use PHP mode
    php_server_port = None
    if php_mode:
        print("PHP mode enabled. Checking for a local PHP server...")
        php_server_port = find_php_server()
        if not php_server_port:
            print("Warning: No PHP server found. PHP files will not be processed.")
            print("Make sure MAMP, XAMPP, or another PHP server is running.")
            print("Falling back to static file mode.")
            php_mode = False

    # Create the appropriate handler
    if php_mode and php_server_port:
        print(f"Using PHP proxy mode with local server on port {php_server_port}")
        # Create a handler class with the PHP server port
        PHPProxyHandler.php_server_port = php_server_port
        PHPProxyHandler.directory = directory
        PHPProxyHandler.script_dir = os.path.dirname(os.path.abspath(__file__))
        handler = PHPProxyHandler
    else:
        print("Using static file mode (PHP files will not be processed)")
        # Use our custom static file handler
        handler = lambda *args, **kwargs: SiteShareHandler(*args, directory=directory, **kwargs)

    # Bind to all interfaces (both IPv4 and IPv6 if available)
    address = ("", port)
    max_retries = 3
    retries = 0

    while retries < max_retries:
        try:
            # Use TCPServer for proper network handling
            with http.server.ThreadingHTTPServer(address, handler) as httpd:
                local_ip = get_local_ip()
                abs_dir = os.path.abspath(directory)
                print(f"\nServing website from directory: {abs_dir}")
                print(f"  - Access locally (on this machine): http://localhost:{port}")
                print(f"  - Access on network (other devices): http://{local_ip}:{port}")
                print("\nImportant:")
                print("  - 'localhost' only works on the computer running this script.")
                print("  - Other devices MUST use the network IP address.")
                print("  - Ensure your firewall allows incoming connections on port {port}.")
                print("\nPress Ctrl+C to stop the server.")
                httpd.serve_forever() # Blocks here until interrupted
        except OSError as e:
            # Handle common errors across platforms
            if e.errno in (errno.EADDRINUSE, 98, 48, 10048): # Linux/macOS/Windows 'Address already in use'
                retries += 1
                print(f"\nError: Port {port} is already in use.")
                if retries < max_retries:
                    try:
                        new_port_str = input(f"Enter a different port (attempt {retries}/{max_retries-1}) or press Enter to exit: ")
                        if not new_port_str:
                            print("Exiting.")
                            sys.exit(1)
                        new_port = int(new_port_str)
                        if 1 <= new_port <= 65535:
                            port = new_port
                            address = ("0.0.0.0", port) # Update address tuple
                        else:
                            print("Invalid port number. Must be between 1 and 65535.")
                            # Decrement retries because this wasn't a valid attempt at a new port
                            retries -=1
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                        # Decrement retries because this wasn't a valid attempt at a new port
                        retries -=1
                else:
                    print("Maximum retry attempts reached. Exiting.")
                    sys.exit(1)
            elif e.errno in (errno.EACCES, 13): # Permission denied (e.g., using < 1024 without root)
                print(f"\nError: Permission denied to use port {port}.")
                print("Try a port number above 1024 or run with administrator/root privileges.")
                sys.exit(1)
            else:
                # Catch other potential OS errors
                print(f"\nAn unexpected OS error occurred: {e}")
                sys.exit(1)
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\nStopping the server...")
            break # Exit the while loop
        except Exception as e:
            # Catch any other unexpected errors during server setup/run
            print(f"\nAn unexpected error occurred: {e}")
            sys.exit(1)

    if retries >= max_retries:
         print("Failed to start server after multiple attempts.")

def print_banner():
    """
    Print a banner with the SiteShare name and version.
    """
    print(f"""
╔═══════════════════════════════════════════╗
║                                           ║
║   SiteShare v{VERSION}                        ║
║   Local Website Sharing Tool              ║
║                                           ║
╚═══════════════════════════════════════════╝
    """)

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

    # Print system information
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")

    # Validate port range
    if not (1 <= args.port <= 65535):
        print(f"Error: Invalid port number {args.port}. Must be between 1 and 65535.")
        return 1

    # Determine directory to serve
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
            print("\nNo websites found in common web server directories.")
            print("Please specify a directory with --dir option.")
            return 1

        print("\nAvailable websites:")
        for i, (path, site) in enumerate(all_sites, 1):
            print(f"{i}. {site} (in {path})")

        selection = input("\nEnter site number (or 'x' to cancel): ").strip()
        if selection.lower() == 'x':
            print("Cancelled.")
            return 0

        try:
            selected_idx = int(selection) - 1
            path, site = all_sites[selected_idx]
            target_dir = os.path.join(path, site)
        except (ValueError, IndexError):
            print("Invalid selection")
            return 1
    else:
        # Use explicitly specified directory
        target_dir = os.path.abspath(target_dir)

    # Security warnings
    print("\n############################################")
    print("#          WARNING: NETWORK EXPOSURE         #")
    print("############################################")
    print("# This script makes the specified directory:")
    print(f"#  '{target_dir}'")
    print("# accessible to ALL devices on your local network.")
    print("#")
    print("# - Ensure you trust your network environment.")
    print("# - Do NOT serve directories containing sensitive data.")
    print("# - Stop the server (Ctrl+C) when finished.")
    print("############################################\n")

    try:
        # Start the server
        run_server(directory=target_dir, port=args.port, php_mode=args.php)
        print("\nServer stopped.")
        return 0
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

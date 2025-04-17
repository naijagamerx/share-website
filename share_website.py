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
    else:
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
    directory = None # Base directory being shared
    script_dir = None

    def __init__(self, *args, **kwargs):
        # Note: The 'directory' attribute is set by run_server before handler instantiation
        # We don't need to pass it to the superclass init for BaseHTTPRequestHandler
        super().__init__(*args, **kwargs)

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

        # --- Special handling for root path ---
        # If accessing the root path, check if we have an index file
        if self.path == '/':
            # Check for standard index files within the serving directory
            for index_file in ['index.php', 'index.html', 'index.htm', 'default.php', 'default.html', 'default.htm']:
                index_path = os.path.join(os.getcwd(), index_file)
                if os.path.exists(index_path):
                    self.log_message(f"Found index file: {index_path} for root path")
                    # If we found index.php, use it directly
                    if index_file.endswith('.php'):
                        self.path = f'/{index_file}'
                    break

        # --- Construct Target URL ---
        # Get the base directory name from the full path
        base_dir_name = os.path.basename(os.path.normpath(self.directory))

        # Forward the request to the PHP server, including the base directory name
        # This ensures we're accessing the correct directory on the PHP server
        target_url = f"http://localhost:{self.php_server_port}/{base_dir_name}{self.path}"

        # --- Log Proxy Action ---
        # Use log_message for consistent formatting and color
        self.log_message(f"Proxying {method} {self.path} -> {target_url}")

        try:
            # --- Prepare Request ---
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

            # --- Send Request and Handle Response ---
            with urllib.request.urlopen(req, timeout=10) as response: # Added timeout
                # Log PHP server response status
                self.log_message(f"PHP Server ({target_url}) responded: {response.status}")

                # Copy the response status and headers from PHP server
                self.send_response(response.status)
                for header, value in response.getheaders():
                    # Avoid copying headers that interfere with proxying
                    if header.lower() not in ('transfer-encoding', 'connection', 'content-encoding'):
                        self.send_header(header, value)
                self.end_headers()

                # Copy the response body from PHP server to client
                try:
                    shutil.copyfileobj(response, self.wfile)
                except (socket.timeout, ConnectionResetError, BrokenPipeError) as copy_err:
                    # Log client-side errors during copy
                    self.log_error(f"Client connection error during proxy response: {copy_err}")

        except urllib.error.HTTPError as e:
            # Log error from PHP server
            self.log_error(f"HTTP Error from PHP server ({target_url}): {e.code} {e.reason}")

            # --- Welcome Page Fallback on Root 404 ---
            # If the PHP server returns 404 for the root path, check for index files first
            if e.code == HTTPStatus.NOT_FOUND and self.path == '/':
                # Check for standard index files within the serving directory
                has_index = False
                for index_file in ['index.html', 'index.htm', 'index.php', 'default.html', 'default.htm', 'default.php']:
                    index_path = os.path.join(os.getcwd(), index_file)
                    if os.path.exists(index_path):
                        has_index = True
                        self.log_message(f"Found index file: {index_path}, but PHP server returned 404")
                        break

                # Only show welcome page if no index files exist
                if not has_index:
                    welcome_path = os.path.join(self.script_dir, 'welcome.html')
                    if os.path.exists(welcome_path):
                        try:
                            with open(welcome_path, 'rb') as file:
                                self.send_response(HTTPStatus.OK)
                                self.send_header('Content-type', 'text/html')
                                self.end_headers()
                                self.wfile.write(file.read())
                                self.log_message("Served welcome.html as fallback for root 404")
                            return # Served welcome page successfully
                        except Exception as welcome_err:
                            self.log_error(f"Error serving welcome page fallback: {welcome_err}")
                            # Fall through to sending the original error if welcome page fails

            # --- Pass Through PHP Server Error ---
            # Otherwise, pass the original error from the PHP server to the client
            self.send_response(e.code, e.reason)
            for header, value in e.headers.items():
                 if header.lower() not in ('transfer-encoding', 'connection', 'content-encoding'):
                    self.send_header(header, value)
            self.end_headers()
            if e.fp: # If the error response has a body, copy it
                try:
                    shutil.copyfileobj(e.fp, self.wfile)
                except (socket.timeout, ConnectionResetError, BrokenPipeError) as copy_err:
                    self.log_error(f"Client connection error during proxy error response: {copy_err}")

        except Exception as e:
            # Log general proxy errors
            self.log_error(f"Exception during proxy request ({target_url}): {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Proxy Error: {e}")

    # Override log_message and log_error for consistent colored output
    def log_message(self, format, *args):
        """Log an arbitrary message with color."""
        message = format % args
        # Determine color based on message content (simple heuristic)
        if "PHP Server" in message and "responded: 2" in message: # PHP 2xx
             log_color = C_GREEN
        elif "PHP Server" in message and "responded: 3" in message: # PHP 3xx
             log_color = C_BLUE
        elif "PHP Server" in message and ("responded: 4" in message or "responded: 5" in message): # PHP 4xx/5xx
             log_color = C_YELLOW
        elif "Proxying" in message:
             log_color = C_CYAN
        else:
             log_color = C_DIM # Default

        sys.stderr.write(f"{log_color}[{self.log_date_time_string()}] {message}{C_RESET}\n")

    def log_error(self, format, *args):
        """Log an error message in red."""
        message = format % args
        sys.stderr.write(f"{C_RED}[{self.log_date_time_string()}] ERROR: {message}{C_RESET}\n")

class SiteShareHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom request handler for SiteShare (Static File Serving).

    Serves files relative to the specified directory and provides
    a welcome page for root requests if no index file exists.
    """
    def __init__(self, *args, directory=None, **kwargs):
        # Ensure directory is absolute for consistency and security
        self.directory = os.path.abspath(directory if directory else ".")
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        # Pass the absolute directory to the parent class constructor
        # SimpleHTTPRequestHandler will serve files relative to this directory
        super().__init__(*args, directory=self.directory, **kwargs)

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

        # --- Welcome Page Logic ---
        # Serve welcome page ONLY for root request IF no standard index file exists
        # The parent handler (super().do_GET()) correctly looks for index files
        # relative to self.directory.
        if self.path == '/':
            has_index = False
            # Check for standard index files within the serving directory
            for index_file in ['index.html', 'index.htm', 'index.php', 'default.html', 'default.htm', 'default.php']:
                # Include PHP files in the check, even though they won't be processed in static mode
                # This prevents showing the welcome page when an index.php exists
                index_path = os.path.join(self.directory, index_file)
                if os.path.exists(index_path):
                    has_index = True
                    print(f"Found index file: {index_path}")
                    break

            if not has_index:
                # No index file found, try serving the custom welcome page
                welcome_path = os.path.join(self.script_dir, 'welcome.html')
                if os.path.exists(welcome_path):
                    try:
                        with open(welcome_path, 'rb') as file:
                            self.send_response(HTTPStatus.OK)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            self.wfile.write(file.read())
                        return # Served welcome page successfully
                    except Exception as e:
                        self.log_error(f"Error serving welcome page: {e}")
                        # Fall through to default handler if reading welcome page fails

        # --- Default File Serving ---
        # For all other requests (including '/' if an index file exists),
        # rely on the parent SimpleHTTPRequestHandler's behavior.
        # It correctly handles paths relative to self.directory.
        # No need for the previous redirect or security checks here.
        super().do_GET()

    # Override log_message to add color
    def log_message(self, format, *args):
        """Log an arbitrary message with color based on status code."""
        message = format % args
        try:
            # Extract status code if available (usually the second arg)
            code = int(args[1])
            if 200 <= code < 300 or code == HTTPStatus.NOT_MODIFIED:
                log_color = C_GREEN
            elif 300 <= code < 400:
                log_color = C_BLUE
            elif 400 <= code < 500:
                log_color = C_YELLOW
            else: # 5xx or other errors
                log_color = C_RED
        except (IndexError, ValueError, TypeError):
            log_color = C_DIM # Default color for non-standard messages

        sys.stderr.write(f"{log_color}[{self.log_date_time_string()}] {message}{C_RESET}\n")

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
        # Use our custom static file handler, passing the directory
        # We need to pass directory="." since we're changing to the target directory
        handler = lambda *args, **kwargs: SiteShareHandler(*args, directory=".", **kwargs)

    # --- Start HTTP Server ---
    original_cwd = os.getcwd() # Store original directory
    try:
        os.chdir(abs_dir_initial) # Change to the target directory
        print(f"{C_DIM}Changed working directory to: {abs_dir_initial}{C_RESET}")

        address = ("", port) # Bind to all interfaces
        max_retries = 3
        retries = 0

        while retries < max_retries:
            try:
                # Use ThreadingHTTPServer for better handling of multiple requests
                # The handler will now serve files relative to the new CWD (abs_dir_initial)
                with http.server.ThreadingHTTPServer(address, handler) as httpd:
                    local_ip = get_local_ip()

                    print_separator("═", 60, C_BLUE)
                    print(f"{C_GREEN}Server started successfully!{C_RESET}")
                    print(f"{C_WHITE}Serving from: {C_BOLD}{abs_dir_initial}{C_RESET}") # Now CWD
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
        if retries >= max_retries:
             print(f"{C_BOLD}{C_RED}Failed to start server after multiple attempts.{C_RESET}")

    finally:
        # --- Change back to original directory ---
        # This block executes whether the try block completed successfully,
        # raised an exception, or was interrupted (like Ctrl+C).
        os.chdir(original_cwd)
        print(f"\n{C_DIM}Restored working directory to: {original_cwd}{C_RESET}")

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

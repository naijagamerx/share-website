import http.server
import socketserver
import socket
import os
import sys

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Create a socket to determine the outgoing IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google's public DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # Fallback to hostname resolution
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"  # Localhost as last resort

def run_server(directory=None, port=8000):
    """Run a simple HTTP server."""
    # Change to the specified directory if provided
    if directory and os.path.isdir(directory):
        os.chdir(directory)
        print(f"Serving from directory: {os.path.abspath(directory)}")
    else:
        print(f"Serving from current directory: {os.path.abspath('.')}")
    
    # Create a handler for the HTTP server
    handler = http.server.SimpleHTTPRequestHandler
    
    # Create a TCP server that allows address reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    # Create and start the server
    with socketserver.TCPServer(("", port), handler) as httpd:
        local_ip = get_local_ip()
        print(f"\nServer started at:")
        print(f"- Local URL: http://localhost:{port}")
        print(f"- Network URL: http://{local_ip}:{port}")
        print("\nPress Ctrl+C to stop the server.")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Simple HTTP Server")
    parser.add_argument("--dir", type=str, help="Directory to serve")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    args = parser.parse_args()
    
    # Run the server
    run_server(args.dir, args.port)

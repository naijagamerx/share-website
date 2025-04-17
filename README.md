# SiteShare

A simple, powerful tool to share local websites across your network - perfect for testing websites on phones, tablets, and other computers.

## Overview

SiteShare is a user-friendly Python utility that makes it easy to share local websites and directories over your local network. It's perfect for:

- Web developers who need to test sites on multiple devices
- Sharing files quickly between computers on the same network
- Previewing MAMP/XAMPP/WAMP projects on other devices
- Testing responsive designs on real devices

## Features

- Simple interface with minimal setup required
- Automatic local IP detection
- Interactive site selection from MAMP/XAMPP directory
- **PHP Support** - Can proxy requests to your local MAMP/XAMPP server
- Detailed security warnings
- Port conflict resolution
- Cross-platform compatibility (Windows, Mac, Linux)

## Installation

### Quick Start (Run Without Installing)

You can run SiteShare directly without downloading the full repository:

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/naijagamerx/share-website/main/install.ps1 | iex
```

**Mac/Linux (Terminal):**
```bash
curl -sSL https://raw.githubusercontent.com/naijagamerx/share-website/main/install.sh | bash
```

This will download and run the script temporarily. For regular use, we recommend installing the full repository as described below.

### For Non-Technical Users

1. **Download the Project**:
   - Click the green "Code" button on this page
   - Select "Download ZIP"
   - Extract the ZIP file to a location on your computer

2. **Run the Application**:
   - On Windows: Double-click the `start_siteshare.bat` file
   - On Mac/Linux: Open Terminal, navigate to the folder, and type `python share_website.py`

### For Developers

```bash
# Clone the repository
git clone https://github.com/naijagamerx/share-website.git

# Navigate to the directory
cd share-website

# Install as a package (optional)
pip install -e .
```

## Usage Guide

### Starting the Application

**Windows Users**:
1. Double-click the `start_siteshare.bat` file
2. A command window will open
3. If you have MAMP or XAMPP installed, you'll see a list of your websites
4. Type the number of the website you want to share and press Enter

**Mac/Linux Users**:
1. Open Terminal
2. Navigate to the folder where you extracted the files
3. Type `python share_website.py` and press Enter
4. Follow the on-screen instructions

### Sharing a Specific Folder

**Windows Users**:
1. Right-click on `start_siteshare.bat` and select "Edit"
2. Change the line to: `python share_website.py --dir "C:\path\to\your\folder"`
3. Save and close the file
4. Double-click the `start_siteshare.bat` file to run it

**Mac/Linux Users**:
1. Open Terminal
2. Navigate to the folder where you extracted the files
3. Type `python share_website.py --dir "/path/to/your/folder"` and press Enter

### Accessing Your Shared Website

1. After starting the application, you'll see two URLs:
   - `http://localhost:8000` - Use this on the computer running the application
   - `http://192.168.x.x:8000` - Use this on other devices on your network

2. On other devices (phones, tablets, other computers):
   - Open a web browser
   - Type the network URL (the one with 192.168.x.x) into the address bar
   - Your website should now be visible on that device

### Examples

```bash
# Share current directory on port 8000 (default)
python share_website.py

# Share a specific directory on port 8080
python share_website.py --dir "C:\My Website" --port 8080

# Share a MAMP/XAMPP website (interactive selection)
python share_website.py

# Enable PHP processing (requires MAMP/XAMPP running)
python share_website.py --php

# Force static file serving mode (even if PHP server detected)
python share_website.py --static
```

## Advanced Usage

### Using the Package in Your Own Python Code

You can also use SiteShare as a library in your own Python code:

```python
# Import the functions from share_website
from share_website import get_local_ip, run_server

# Get the local IP address
ip = get_local_ip()
print(f"Your local IP address is: {ip}")

# Start a server in a specific directory
run_server(directory="/path/to/your/website", port=8080)
```

See the `examples/simple_usage.py` file for a complete example.

### Running Tests

If you want to run the tests to make sure everything is working correctly:

1. Open a command prompt or terminal
2. Navigate to the SiteShare folder
3. Run one of the following commands:

```bash
# Using pytest (if installed)
python -m pytest

# Using the built-in unittest module
python -m unittest discover tests

# Using the Makefile (on Mac/Linux)
make test
```

## MAMP/XAMPP Integration

SiteShare automatically detects websites in your MAMP or XAMPP htdocs folder:

- For MAMP, it looks in `c:/MAMP/htdocs/` (Windows) or `/Applications/MAMP/htdocs/` (Mac)
- For XAMPP, it looks in `c:/xampp/htdocs/` (Windows) or `/opt/lampp/htdocs/` (Linux)

If you have either of these installed, SiteShare will show you a list of available websites when you run it without specifying a directory.

### PHP Support

SiteShare can process PHP files by proxying requests to your local MAMP/XAMPP/WAMP server.

**How it works:**

1.  **Detection:** When started, SiteShare checks common ports (80, 8888, 8080, 8000) for a running PHP-capable server (like Apache or Nginx often used by MAMP/XAMPP).
2.  **Mode Selection:**
    *   **`--php` flag:** If you run `python share_website.py --php` and a PHP server is found, PHP proxy mode is automatically enabled.
    *   **`--static` flag:** If you run `python share_website.py --static`, static file serving mode is forced, regardless of whether a PHP server is found.
    *   **No flags:** If a PHP server is detected and you didn't use `--php` or `--static`, SiteShare will ask you interactively: `Enable PHP proxy mode for this site? (y/n):`. Choose `y` to enable PHP proxying or `n` to use static file serving for this session.
    *   **No PHP Server:** If no PHP server is detected on the common ports, SiteShare will default to static file serving mode.
3.  **Proxying:** In PHP mode, requests for `.php` files (and potentially other requests depending on the setup) are forwarded to your local PHP server for processing. The results are then sent back to the requesting device.

**Benefits:**

This allows you to view and interact with PHP-based websites on other devices, including:
- WordPress sites
- PHP applications
- Dynamic websites with database connections

> **Note:** PHP proxy mode requires that you have MAMP, XAMPP, WAMP, or a similar PHP development server running locally on one of the detected ports. Static mode does not require a separate PHP server.

## Troubleshooting

### "Address already in use" error

This means another program is already using the port (usually 8000). You can:
1. Enter a different port number when prompted
2. Specify a different port with `--port`, e.g., `python share_website.py --port 8080`

### Can't access from other devices

1. Make sure all devices are on the same network
2. Check if your firewall is blocking the connection
3. Try using a different port (some networks block common ports)

## Security Considerations

This tool makes the specified directory accessible to all devices on your local network. Please be aware of the following security considerations:

- Only use this tool on trusted networks (like your home network)
- Do not share directories containing sensitive information
- Stop the server when you're done using it
- This is not intended for production use or exposure to the internet

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Python's http.server module
- Inspired by the need for simple local network sharing

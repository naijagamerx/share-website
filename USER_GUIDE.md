# SiteShare User Guide

This guide will help you use SiteShare to share your websites with other devices on your network.

## What is SiteShare?

SiteShare is a simple tool that lets you view your website on other devices like phones, tablets, or other computers. This is useful for:

- Testing how your website looks on different devices
- Showing your website to others without uploading it to the internet
- Quickly sharing files between computers

## Getting Started

### On Windows:

1. Double-click the `start_siteshare.bat` file
2. A black command window will open
3. If you have MAMP, XAMPP, or WAMP installed, you'll see a list of your websites
4. Type the number of the website you want to share and press Enter
5. You'll see two web addresses (URLs):
   - One starting with "localhost" (for your computer)
   - One starting with numbers like "192.168.x.x" (for other devices)

### On Mac:

1. Open Terminal (find it in Applications > Utilities)
2. Type `cd ` (with a space after it)
3. Drag the SiteShare folder onto the Terminal window (this fills in the path)
4. Press Enter
5. Type `chmod +x start_siteshare.sh` and press Enter
6. Type `./start_siteshare.sh` and press Enter
7. Follow the on-screen instructions

## Viewing Your Website on Other Devices

1. Make sure all devices are connected to the same Wi-Fi network
2. On your other device (phone, tablet, etc.):
   - Open a web browser (like Chrome, Safari, or Firefox)
   - Type the address that starts with numbers (like http://192.168.x.x:8000)
   - Your website should appear!

## Troubleshooting

### Can't see the website on other devices?

1. Make sure all devices are on the same network
2. Try turning off your firewall temporarily
3. Try a different port by running: `python share_website.py --port 8080`

### "Address already in use" error?

This means another program is using the same port. You can:
1. Enter a different port number when prompted
2. Close other web servers or applications that might be using the port

### Need more help?

Check the README.md file for more detailed instructions or open an issue on GitHub.

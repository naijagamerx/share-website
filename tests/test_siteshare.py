#!/usr/bin/env python3
"""
Unit tests for SiteShare.

Run with: python -m unittest tests/test_siteshare.py
"""

import unittest
import sys
import os
import socket

# Add the parent directory to the path so we can import share_website
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from share_website import get_local_ip

class TestSiteShare(unittest.TestCase):
    """Test cases for SiteShare functions."""
    
    def test_get_local_ip(self):
        """Test that get_local_ip returns a valid IP address."""
        ip = get_local_ip()
        # Check that the result is a string
        self.assertIsInstance(ip, str)
        
        # Check that it's a valid IP format (simple check)
        parts = ip.split('.')
        self.assertEqual(len(parts), 4, "IP address should have 4 parts separated by dots")
        
        # Check that each part is a number between 0 and 255
        for part in parts:
            try:
                num = int(part)
                self.assertTrue(0 <= num <= 255, f"IP part {part} should be between 0 and 255")
            except ValueError:
                self.fail(f"IP part {part} should be a number")
        
        # Check that it's not the loopback address (unless that's all we have)
        # This test might fail if the machine has no network connection
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            s.close()
            # If we can connect to the internet, the IP shouldn't be 127.0.0.1
            self.assertNotEqual(ip, "127.0.0.1", "IP should not be loopback if network is available")
        except OSError:
            # If we can't connect, then loopback is acceptable
            pass

if __name__ == '__main__':
    unittest.main()

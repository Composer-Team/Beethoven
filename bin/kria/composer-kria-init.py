#!/usr/bin/python3

import os
import sys

"""
Copy over initialization scripts onto Kria
"""

if os.environ.get("KRIA_IP") is None:
    print("Please define KRIA_IP environment variable")
    exit(1)

kria_ip = os.environ['KRIA_IP']

os.system(f"scp -r {os.environ['BEETHOVEN_ROOT']}/bin/kria/bin petalinux@{kria_ip}:~/")
os.system(f"ssh petalinux@{kria_ip} chmod u+x bin/beethoven-load-design.py")
print("make sure that you export path to include the $HOME/bin directory in the ~/.bashrc")





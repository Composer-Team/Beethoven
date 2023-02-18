#!/usr/bin/python3

import os
import sys

"""
Copy over initialization scripts onto Kria
"""

if os.environ.get("KRIA_IP") is None:
    print("Please define KRIA_IP environment variable")
    exit(1)

os.system(f"scp -r {os.environ['COMPOSER_ROOT']}/bin/kria/bin petalinux@{os.environ['KRIA_IP']}:~/")
print("make sure that you export path to include the $HOME/bin directory in the ~/.bashrc")





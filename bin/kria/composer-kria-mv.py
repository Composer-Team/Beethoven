#!/usr/bin/python3

import os

"""
Prepare files for flashing on the FPGA
"""

if os.environ.get('KRIA_IP') is None:
    print("Please define KRIA_IP environment variable")

kria_ip = os.environ['KRIA_IP']

os.system(f"scp {os.environ['COMPOSER_ROOT']}/Composer-Hardware/vsim/generated-src/composer_allocator")


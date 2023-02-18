#!/usr/bin/python3

import os
import sys

"""
Copy over initialization scripts onto Kria
"""

os.system(f"scp -r {os.environ['COMPOSER_ROOT']}/bin/kria/bin petalinux@kria-fpga.cs.duke.edu:~/")
print("make sure that you export path to include the $HOME/bin directory in the ~/.bashrc")





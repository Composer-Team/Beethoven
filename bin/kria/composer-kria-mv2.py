#!/usr/bin/python3

import os
import subprocess
import sys


command = ["ssh", "petalinux@" + os.environ['KRIA_IP'], 'source ~/.bashrc && echo "$COMPOSER_ROOT"']
child = subprocess.run(command, capture_output = True)
endpoint = child.stdout.decode("utf-8").strip()



sources = filter(lambda x: x[-2:] == '.h' or x[-3:] == '.cc', list(os.walk(os.environ['COMPOSER_ROOT'] + "/Composer-Hardware/vsim/generated-src"))[0][2])
for s in sources:
    subprocess.run(["scp", f"{os.environ['COMPOSER_ROOT']}/Composer-Hardware/vsim/generated-src/{s}", f"petalinux@{os.environ['KRIA_IP']}:{endpoint}/Composer-Hardware/vsim/generated-src/"])

exit


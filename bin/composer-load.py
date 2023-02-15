

import os
import sys
import json
import subprocess

proc = subprocess.Popen(["aws", "ec2", "describe-fpga-images", "--owner", "self"], stdout=subprocess.PIPE, shell=True)
(out, err) = proc.communicate()

strout = out.decode("utf-8")
images = json.load(strout)

print(images)


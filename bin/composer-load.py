#!/usr/bin/python3

import os
import sys
import json
import subprocess

# aws ec2 describe-fpga-images --owner self
proc = os.popen("aws ec2 describe-fpga-images --owner self")
images = json.load(proc)
#print(images['FpgaImages'])
print([i['Name'] for i in images['FpgaImages']])



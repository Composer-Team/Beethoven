#!/usr/bin/python3

import os
import json

# Make sure that Composer directory exists
if os.environ.get('COMPOSER_ROOT') is None:
    print("You must define the $COMPOSER_ROOT environment variable. We expect it to be the top-level of the"
          " Composer repo.")
    exit(1)

# Make sure that xdma is setup and working, otherwise set it up
xdmas = list(os.walk("/dev"))[0][2]
if len(list(filter(lambda x: "xdma" in x, xdmas))) == 0:
    os.system(f"cd {os.environ['COMPOSER_ROOT']} && git clone https://github.com/aws/aws-fpga.git || true"
              f" && cd aws-fpga/sdk/linux_kernel_drivers/xdma/ && make && sudo insmod xdma.ko")

# aws ec2 describe-fpga-images --owner self
proc = os.popen("aws ec2 describe-fpga-images --owner self")
images = json.load(proc)['FpgaImages']
names = [i['Name'] for i in images]

for idx, nm in enumerate(names):
    print(f"\t[{idx}] - {nm}")

choice = int(input("Select an image to load\n"))
assert len(names) > choice >= 0
os.system("sudo fpga-load-local-image -S 0 -I " + str(images[choice]['FpgaImageGlobalId']))





#!/bin/bash

git clone https://github.com/aws/aws-fpga.git
cd aws-fpga || exit
sudo yum groupinstall "Development tools"
sudo yum install kernel kernel-devel
sudo systemctl stop mpd || true
sudo yum remove -y xrt xrt-aws || true
source sdk_setup.sh
cd sdk/linux_kernel_drivers/xdma || exit
make && sudo make install
echo "If the kernel module is running (and working), you should see some files below:"
ls /dev/xdma
echo "If there's nothing printed out above, try restarting the F1 instance."
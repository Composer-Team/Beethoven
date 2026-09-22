#!/bin/bash

sudo dnf install openssh git vim cmake gcc binutils g++ --allowerasing
sudo dnf remove dropbear
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/aarch64-xilinx-linux-gcc-11.2.0 50
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/aarch64-xilinx-linux-g++ 50
#!/usr/bin/bash

git clone https://github.com/aws/aws-fpga.git -q || true
cd aws-fpga
source sdk_setup.sh


echo 'export PATH=$PATH:$HOME/bin' >> ~/.bashrc
mkdir -p build-dir/generated-src
cp ~/bin/aws/scripts/Makefile build-dir/

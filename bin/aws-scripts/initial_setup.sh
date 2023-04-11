#!/usr/bin/bash

git clone https://github.com/aws/aws-fpga.git || true
echo 'export PATH=$PATH:$HOME/bin' >> ~/.bashrc
mkdir -p build-dir/generated-src
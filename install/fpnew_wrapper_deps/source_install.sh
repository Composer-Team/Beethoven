#!/bin/bash
echo "TRYING TO INSTALL SystemVerilog-to-Verilog Converter. May ask for root permissions..."
echo "NOTE: If you're using Ubuntu, using the ubuntu_install.sh script will take much less time and less disk."

if ! type "stack" > /dev/null; then
  echo "Couldn't find Haskell stack installation. Trying to install now."
  wget -qO- https://get.haskellstack.org/ | sh
fi

git clone https://github.com/zachjs/sv2v.git
cd sv2v
sudo make
cd ..

echo "TRYING TO INSTALL Yosys synthesis suite. This may take a while. We will also ask for root permissions. We require homebrew to install dependencies."
git clone https://github.com/YosysHQ/yosys.git
cd yosys

if type "yum" > /dev/null; then
  sudo yum install build-essential clang bison flex libreadline-devel gawk tcl-devel libffi-devel git graphviz xdot pkg-config python3 libboost-system-devlibboost-python-devel libboost-filesystem-dev zlib1g-devel
elif type "apt-get" > /dev/null; then
  sudo apt-get install build-essential clang bison flex libreadline-dev gawk tcl-dev libffi-dev git graphviz xdot pkg-config python3 libboost-system-dev libboost-python-dev libboost-filesystem-dev zlib1g-dev
else
  echo "Can't find apt-get or yum. Don't know how to install dependencies..."
  exit 1
fi

make
sudo make install


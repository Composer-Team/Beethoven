echo "TRYING TO INSTALL SystemVerilog-to-Verilog Converter. May ask for root permissions..."
wget https://github.com/zachjs/sv2v/releases/download/v0.0.10/sv2v-Linux.zip
unzip sv2v-Linux.zip
sudo cp sv2v-Linux/sv2v /usr/local/bin
rm -rf sv2v-Linux sv2v-Linux.zip

echo "TRYING TO INSTALL Yosys synthesis suite. This may take a while. We will also ask for root permissions."
git clone https://github.com/YosysHQ/yosys.git
cd yosys
sudo apt-get install build-essential clang bison flex libreadline-dev gawk tcl-dev libffi-dev git graphviz xdot pkg-config python3 libboost-system-dev libboost-python-dev libboost-filesystem-dev zlib1g-dev
make
sudo make install


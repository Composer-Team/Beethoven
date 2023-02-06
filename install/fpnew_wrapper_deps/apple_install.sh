echo "TRYING TO INSTALL SystemVerilog-to-Verilog Converter. May ask for root permissions..."
wget https://github.com/zachjs/sv2v/releases/download/v0.0.10/sv2v-macOS.zip
unzip sv2v-macOS.zip
sudo cp sv2v-macOS/sv2v /usr/local/bin
rm -rf sv2v-macOS.zip sv2v-macOS

echo "TRYING TO INSTALL Yosys synthesis suite. This may take a while. We will also ask for root permissions. We require homebrew to install dependencies."
git clone https://github.com/YosysHQ/yosys.git
cd yosys
brew tap Homebrew/bundle && brew bundle
make
sudo make install


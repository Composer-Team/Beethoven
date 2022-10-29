# Composer

# Prerequisites 

To use the Composer framework, the only necessary installations are [sbt](https://www.scala-sbt.org) and CMake.

Linux Installation:
```shell
sudo apt-get install cmake sbt
```

Mac(homebrew) Installation: (Note that these packages can be installed from source without homebrew)
```shell
brew install cmake sbt
```

# Backends

### Verilator

We currently use a Verilator backend for simulation. We may add additional simulation backends in the future.
[Verilator Installation Link](https://verilator.org/guide/latest/install.html)
Do not use `brew` or `apt` to install Verilator as it may be an old version.
It _may_ work but is not guaranteed to be tested or functional.

### AWS F1
Clone the [Amazon AWS FPGA SDK](https://github.com/aws/aws-fpga) into your desired install directory.
```shell
git clone --recursive https://github.com/aws/aws-fpga.git
```
In order for the Composer tools to find the SDK, export the installation path to the `COMPOSER_AWS_SDK_DIR` variable
within your `.bashrc` file.
```shell
echo "export COMPOSER_AWS_SDK_DIR=<path_to_sdk>" >> .bashrc
```



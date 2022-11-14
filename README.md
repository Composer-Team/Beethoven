# Composer
This Composer is made to help design and simulate hardware for FPGAs.

## Prerequisites
### [sbt](https://www.scala-sbt.org) and CMake
sbt is required to compile Chisel programs, and CMake is required to compile C++ programs.

#### Linux Installation:
```shell
sudo apt-get install cmake sbt
```

#### Mac(homebrew) Installation:
Note that these packages can be installed from source without homebrew
```shell
brew install cmake sbt
```

### JDK 17 (or older)
sbt requires JDK 17 or older to run, the newer versions ov Java will not work.
To check the current java version, use
```bash
java -version
```
To switch to java 17 within a specific terminal window, first [install it](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html) if it is not already installed, then use
```bash
JAVA_HOME=`/usr/libexec/java_home -v 17`
```

### Verilator [(Verilator Installation Link)](https://verilator.org/guide/latest/install.html)
Verilator is used as a backend for simulation. Additional simulation backends may be added in the future.
Do not use `brew` or `apt` to install Verilator as it may be an old version.
It _may_ work but is not guaranteed to be tested or functional.

### AWS-F1
Clone the [Amazon AWS FPGA SDK](https://github.com/aws/aws-fpga) into your desired install directory.
```shell
git clone --recursive https://github.com/aws/aws-fpga.git
```
In order for the Composer tools to find the SDK, export the installation path to the `COMPOSER_AWS_SDK_DIR` variable
within your `.bashrc` or `.zshrc` file by adding the following line.
```shell
export COMPOSER_AWS_SDK_DIR=<path_to_sdk>
```


# Recommended Setup
Begin by cloning this parent repo: [Composer](https://github.com/ChrisKjellqvist/Composer).
```bash
git clone https://github.com/ChrisKjellqvist/Composer-Hardware.git
```
Then run the setup script that will clone dependencies, patch them, and set up some environment variables.
```bash
./setup.sh
```
The installation script may tell you to add some variables to your path after installation so pay attention for those messages.
This will involve adding the following lines to `.bashrc` or `.zshrc`
```bash
export COMPOSER_ROOT=<Path to Composer Repository>/Composer
export PATH=$PATH:$COMPOSER_ROOT/bin
```

# Build and Simulate an Example
We will begin by building and simulating some example programs that are already in the repository.
The example hardware is located in `Composer/Composer-Hardware/src/main/scala/design`.

`Examples` contains chisel hardware descriptions of 3 different Cores (a LFSR, an ALU, and a Vector Adder).

`Example Configs` contains a configuration for each of those to interface with the Composer, and an
additional configuration called `exampleConfig` that combines all three into one.

The example software is located in `Composer/Composer-Examples`

All the `.cc` files are different software tests that will be run on the hardware that is built.

## Building

To build the hardware associated with `exampleConfig`, run the following:
```shell
cd vsim
make verilog CONFIG=design.exampleConfig
```

Now, the verilog sources corresponding to the accelerator design should be in the generated-src directory found within
vsim.

Some additional steps are necessary to preparing these sources for F1 image creation. **NOTE**: this should be
scripted away before release to the public.

## Simulation

Once you've built the verilog sources, you can simulate them using the following sequence of commands:
```shell
# move into the directory that contains the built files. 
cd examples
# prepare the hardware files for simulation.
composer-make
# Move to the directory with the software files
cd ../../../Composer-Examples
# Create a build directory to contain ouptut files
mkdir build
cd build
# Compile the software files so they are ready for simulation
cmake ..
make
# Run the simulation
../verilator/Composer_Verilator &> /dev/null &; sleep 1 && ./vector
```
This last command combines two commands. `../verilator/Composer_Verilator &> /dev/null &;` Is the
command to run the simulator. This runs for a bit of time, and anytime while this is running, a simulation
file can be run to analyze it. `./vector` is the simulation file, and it will be analyzed by the simulator that is running.
This could be done in two lines, or even two terminal windows, but it is combined for convenience.

To test the other test files, simply replace `./vector` with the desired test from the build directory, such as `./alutest`.

A `trace.vcd` file will be created in the build directory, and this file can be viewed with a waveform analyzer such
as gtkWave to see how the test performed.

# Your turn!
#### For details on developing your own Core, look at the [Composer-Hardware readme](Composer-Hardware/README.md).

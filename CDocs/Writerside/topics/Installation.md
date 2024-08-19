# Installation

## Hardware Development Installation

The Beethoven development tools are available as an sbt package in the
same way as Chisel.
In your scala build file (`build.sbt` in your project root directory),
simply add Beethoven to the libraryDependencies where you have chisel.

```Scala
lazy val my_project = (project in file("."))
  .settings(
    name := "my_project",
    libraryDependencies ++= Seq(
      "edu.berkeley.cs" %% "chisel3" % "2.3.10",
      "edu.duke.cs.apex" %% "beethoven-hardware" % "beta.0.0.3",
    ),
    addCompilerPlugin("edu.berkeley.cs" % "chisel3-plugin" % chiselVersion cross CrossVersion.full),
  )
```

## Simulation Environment Installation

The installation for simulation environments is different than real
FPGA/ASIC execution environments - but this is usually not a problem because
development machines are usually not the ones where the hardware is
deployed. If you are running on a real machine, see below for installation 
instructions.

### x86_64-linux, aarch64-macos

For x86_64-linux and aarch64-macos platform, we currently have the
packages published on anaconda.

```Bash
# install Beethoven Software and Runtime, respectively
conda install -c chriskjellqvist bsw brt
```
### Manual Installation
There are several components that go into supporting Beethoven,
particularly the FPUs.
- [CMake](https://cmake.org)(>=3.0.0)
- [Verilator](https://github.com/verilator/verilator)(>=v5), for simulation (v5.0.26 verified)
- [Yosys](https://github.com/YosysHQ/yosys), (FPU-only), provides us a workaround for simulation of [SystemVerilog-based FPUs](https://github.com/openhwgroup/cvfpu)
- [sv2v](https://github.com/zachjs/sv2v), (FPU-only), another workaround for SystemVerilog simulation in Verilator

Some of these can be challenging to install on all systems (e.g., mac-os),
which is why we provide the anaconda packages. Nevertheless, manual
installation may occasionally be necessary for other systems.
Do raise a git issue if there is a system that should be supported but
isn't.

First, install the above components with the required versions.
If you do not plan on using FPUs, or plan to use an FPU implementation that
you know is well-supported by Verilator, then you do not need `yosys` or `sv2v`.
Next, install the Beethoven Software Library.


After installing the above dependencies, install the software library. 
Root install makes it easy for CMake to find the package, but it is
possible to do a local install. Just make sure that CMake can find the
installed package.

```Bash
git clone https://github.com/Composer-Team/Beethoven-Software.git bsw
cd bsw && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make
sudo make install
```

#### Kria Modifications

When running on embedded FPGA platforms, perform the following installation.




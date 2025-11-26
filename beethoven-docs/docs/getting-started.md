---
id: getting-started
title: Getting Started
sidebar_label: Getting Started
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Getting Started With Beethoven

Beethoven provides a software and hardware ecosystem for designing, assembling, and deploying hardware accelerators.
Below we show a high-level break-down of Beethoven into its hardware and software components.

<p align="center">
    <map name="GraffleExport">
<area shape="rect" coords="184,291,356,313" href="/docs/platforms/kria"/>
<area shape="rect" coords="509,184,648,206" href="/docs/hardware/overview/#platforms"/>
<area shape="rect" coords="509,68,648,90" href="/docs/hardware/overview/#configuration--build"/>
<area shape="rect" coords="6,291,179,313" href="/docs/platforms/aws-f2"/>
<area shape="rect" coords="6,254,179,276" href="/docs/software/overview/#memory-modeling"/>
<area shape="rect" coords="6,226,179,248" href="/docs/software/overview/#building"/>
<area shape="rect" coords="6,198,179,220" href="/docs/software/overview/#building"/>
<area shape="rect" coords="509,218,648,240" href="https://www.chisel-lang.org"/>
<area shape="rect" coords="370,272,618,294" href="/docs/platforms/custom-platform"/>
<area shape="rect" coords="6,115,179,137" href="/docs/software/overview/#communicating-with-the-accelerator"/>
<area shape="poly" coords="306,254,306,31,284,31,284,254,306,254" href="/docs/hardware/overview/#platforms"/>
<area shape="rect" coords="6,138,179,161" href="/docs/software/overview/#allocating-memory"/>
<area shape="rect" coords="509,131,648,170" href="/docs/hardware/verilog"/>
<area shape="rect" coords="509,99,648,122" href="/docs/hardware/overview/#on-chip-memory-user-managed"/>
<area shape="rect" coords="368,176,479,206" href="/docs/hardware/overview/#on-chip-memory-scratchpad"/>
<area shape="rect" coords="368,145,479,176" href="/docs/hardware/overview/#memory-read-and-write-channels"/>
<area shape="rect" coords="368,115,479,145" href="/docs/hardware/overview/#memory-read-and-write-channels"/>
<area shape="rect" coords="362,223,479,254" href="/docs/hardware/overview/#host-interface"/>
<area shape="rect" coords="1,59,176,90" href="/docs/software/overview/#testbench"/>
<area shape="rect" coords="1,90,184,170" href="/docs/software/overview/#Beethoven-Library"/>
<area shape="rect" coords="1,1,193,281" href="/docs/software/overview"/>
<area shape="rect" coords="362,31,651,254" href="/docs/hardware/overview"/>
<area shape="rect" coords="251,1,651,254" href="/docs/hardware/overview"/>
    </map>
    <img src="/Beethoven-Docs/img/figs/sitemap.jpg" usemap="#GraffleExport"/>

<p> <b>Click the boxes to navigate the site!</b> </p>
</p>

At the center of it all is your hardware accelerator "core" implementation - a single functional unit.
The goal is to make it comfortable to
- **Manage host-accelerator communication from the HW**: Control signals from the host should align to your implemented algorithm and be otherwise straightforward to use.
- **Use this functional unit from the Host**: Software implementations should not need to massively complicate the codebase for utilizing this accelerated function.
- **Manage data**: Regardless of how the memory system is organized on your platform, it should be easy to access memory from your accelerator and read back results from the host. 
- **Scale and Deploy your system**: Beethoven generates platform-aware for your hardware acelerator by simply changing one line!

We will cover each of these points in this documentation. You can click on the blocks in the figure above to explore Beethoven's capabilities, 
or continue on to one of the following major sections:
- [Beethoven HW Stack](/docs/hardware/overview) 
- [Beethoven SW Stack](/docs/software/overview)


### Docker Image

We provide a docker image and VSCode integration that should provide everything you need to get started developing hardware with Beethoven.
[link](https://github.com/Composer-Team/beethoven-template/tree/main/.devcontainer)

### Manrual Environment Setup

Beethoven uses the `BEETHOVEN_PATH` environment variable to export the hardware and generated software for a design.
```bash title="Set up BEETHOVEN_PATH"
mkdir <my-beethoven-dir>
echo "export BEETHOVEN_PATH=`pwd`/my-beethoven-dir" >> ~/.bashrc
```

:::warning
Restart your shell or run `source ~/.bashrc` after setting BEETHOVEN_PATH for the changes to take effect.
:::

If you use a different shell, you can put the equivalent in the corresponding rc file.

#### Dependencies

Beethoven Hardware depends on [sbt](https://www.scala-sbt.org) and a Java version 8-21.
We heavily encourage the use of an IDE for developing Chisel or Beethoven. We internally use the JetBrains [IntelliJ IDE](https://www.jetbrains.com/idea/download/)
and find it very helpful. If you choose to use IntelliJ or a similar IDE, make sure to download the sbt plugin from the plugin
marketplace.

Note: if you are using IntelliJ on a system with a Java version >17, then [see here](/docs/ide/overview) to see how to select the correct Java version inside the IDE - it's somewhat tricky.

Beethoven Software depends on a C++-17 compliant compiler and [CMake](https://www.cmake.org).

#### Beethoven Software Install

The Beethoven Software library is required for both simulating and running your design on real hardware.

<Tabs>
<TabItem value="a" label="Simulation/AWS F2" default>
```bash title="Install for Simulation/AWS F2"
git clone https://github.com/Composer-Team/Beethoven-Software
cd Beethoven-Software
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DPLATFORM=discrete
make -j
sudo make install
```
</TabItem>
<TabItem value="b" label="Zynq">
```bash title="Install for Zynq"
git clone https://github.com/Composer-Team/Beethoven-Software
cd Beethoven-Software
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DPLATFORM=kria
make -j2
sudo make install
```
</TabItem>
<TabItem value="c" label="Non-Root Install">
```bash title="Install without root access"
git clone https://github.com/Composer-Team/Beethoven-Software
cd Beethoven-Software
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DPLATFORM=<discrete/kria> -DCMAKE_INSTALL_PREFIX=<install-dir>
make -j
make install
# add a BEETHOVEN_ROOT export so that cmake can find your non-root install and link appropriately
echo "export BEETHOVEN_ROOT=<install-dir>/lib/cmake" >> ~/.bashrc
```
</TabItem>
</Tabs>

#### Beethoven Runtime Install

The Beethoven Runtime manages the simulator and device backends. You only need to build this when you're ready to run a testbench.

<Tabs>
<TabItem value="a" label="Simulation (Icarus Verilog)" default>
```bash
git clone https://github.com/Composer-Team/Beethoven-Runtime
cd Beethoven-Runtime
bash setup_dramsim.sh
# this will build and run the simulator
make sim_icarus
```
</TabItem>
<TabItem value="b" label="Simulation (VCS)">
```bash
git clone https://github.com/Composer-Team/Beethoven-Runtime
cd Beethoven-Runtime
bash setup_dramsim.sh
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DTARGET=sim -DSIMULATOR=vcs
make -j
../scripts/build_vcs.sh

# run the runtime/simulator
./BeethovenTop
```
</TabItem>
<TabItem value="c" label="Simulation (Verilator)">
```bash
git clone https://github.com/Composer-Team/Beethoven-Runtime
cd Beethoven-Runtime
bash setup_dramsim.sh
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DTARGET=sim -DSIMULATOR=verilator
make -j

# run the runtime/simulator
./BeethovenRuntime
```
</TabItem>
<TabItem value="d" label="AWS F2">
```bash
git clone https://github.com/Composer-Team/Beethoven-Runtime
cd Beethoven-Runtime
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DTARGET=fpga -DBACKEND=F2
make -j

# run the runtime
sudo ./BeethovenRuntime
```
</TabItem>
<TabItem value="e" label="Zynq">
```bash
git clone https://github.com/Composer-Team/Beethoven-Runtime
cd Beethoven-Runtime
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DTARGET=fpga -DBACKEND=Kria
make -j

# run the runtime
sudo ./BeethovenRuntime
```
</TabItem>
</Tabs>

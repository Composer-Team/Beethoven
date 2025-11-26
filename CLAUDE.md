# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Composer is a hardware accelerator development framework centered around **Beethoven**, which generates RTL from high-level Scala configurations and provides runtime software for simulation and FPGA deployment. The project consists of two main submodules:

- **Beethoven-Hardware**: Scala/Chisel codebase for hardware generation (RTL synthesis, protocols, memory systems)
- **Beethoven-Software**: C++ runtime library and simulation infrastructure

## Build Commands

### Hardware Generation (Scala/Chisel)
```bash
cd Beethoven-Hardware
sbt run               # Generate Verilog from Scala configuration
sbt compile           # Compile Scala sources only
```

Hardware builds require the `BEETHOVEN_PATH` environment variable set to the Composer root directory. Generated RTL outputs to `$BEETHOVEN_PATH/build/hw/`.

### Software Runtime Library
```bash
cd Beethoven-Software
mkdir -p build && cd build
cmake .. -DPLATFORM=<platform> \
         -DBEETHOVEN_HARDWARE_PATH=/path/to/Beethoven-Hardware  # Optional
make -j
sudo make install
```

Options:
- `PLATFORM`: `discrete` (simulation), `kria`, or `baremetal`
- `BEETHOVEN_HARDWARE_PATH`: Path to Beethoven-Hardware (saves for unified CMake builds)

Or use the Makefile directly:
```bash
cd Beethoven-Software
make install_swlib PLATFORM=discrete  # For simulation
make install_swlib PLATFORM=kria      # For Kria FPGA
```

### Simulation
```bash
cd Beethoven-Software
make SIMULATOR=icarus      # Icarus Verilog (default)
make SIMULATOR=verilator   # Verilator
make SIMULATOR=vcs         # Synopsys VCS
```

Simulation requires DRAMsim3 library (built automatically):
```bash
make libdramsim3.so
```

### AWS FPGA Flow
```bash
bin/aws-gen-build     # Generate AWS build scripts (requires aws-fpga SDK setup)
```

## Architecture

### Beethoven-Hardware (Scala/Chisel)

Located in `Beethoven-Hardware/src/main/scala/beethoven/`:

| Package | Purpose |
|---------|---------|
| `Config/` | Accelerator configuration (memory channels, scratchpads, accelerator systems) |
| `Systems/` | Top-level accelerator system assembly |
| `Protocol/` | Bus protocols (AXI4, TileLink, RoCC command interface) |
| `MemoryStreams/` | DMA readers, scratchpads, memory controllers |
| `Platforms/` | Target platforms (ASIC, FPGA/Xilinx, Simulation) |
| `Generation/` | Verilog generation, C++ header emission, annotations |
| `Floorplanning/` | SLR partitioning and constraints for multi-die FPGAs |
| `Driver.scala` | Main build entry point (`BeethovenBuild` class) |

To create a new accelerator, extend `BeethovenBuild` with your `AcceleratorConfig` and target `Platform`.

### Beethoven-Software (C++)

| Directory | Purpose |
|-----------|---------|
| `include/beethoven/` | Public headers (rocc_cmd.h, response_handle.h, allocator/) |
| `src/` | Core runtime (command encoding, response handling) |
| `src/fpga_handle_impl/` | Platform-specific FPGA communication |
| `runtime/` | Simulation runtime (memory controllers, VPI interface) |
| `runtime/DRAMsim3/` | DRAM timing simulation (third-party) |

### Supporting Tools (bin/)

- `aws-gen-build`, `aws-build-mv`: AWS FPGA build flow scripts
- `beethoven-load`: Design loading utilities
- `kria/`: Kria FPGA deployment tools

## Key Concepts

- **RoCC Commands**: The accelerator uses RoCC-style command/response protocol between host and accelerator
- **Memory Channels**: Configurable read/write channels for DMA operations
- **Scratchpads**: On-chip memory with configurable banking
- **Platforms**: Hardware backends determine memory interfaces, clock domains, and synthesis targets

## Unified CMake Build System

The preferred way to develop with Beethoven is using the unified CMake build system, which handles both hardware generation (Scala/Chisel) and software compilation in a single build step.

### Example CMakeLists.txt
```cmake
cmake_minimum_required(VERSION 3.15)
project(my_accelerator)
set(CMAKE_CXX_STANDARD 20)

find_package(beethoven REQUIRED)

# Generate hardware from Scala configuration
# Sets BEETHOVEN_PATH locally - outputs go to build/beethoven_my_accel/
beethoven_hardware(my_accel
  MAIN_CLASS com.example.MyAccelBuild    # Scala main class (required)
  PLATFORM discrete                       # discrete|kria|baremetal (default: discrete)
  BUILD_MODE Simulation                   # Simulation|Synthesis (default: Simulation)
  SCALA_ARGS -DPARAM=value               # Optional: pass -D args to sbt
)

# Build testbench with simulator
beethoven_testbench(my_test
  SOURCES test.cc                         # Your testbench sources
  HARDWARE my_accel                       # Reference to hardware target above
  SIMULATOR verilator                     # verilator|icarus|vcs (default: verilator)
)
```

### Build Commands
```bash
mkdir build && cd build
cmake ..
make                 # Generates hardware + builds testbench
./my_test            # Run simulation
```

### How It Works
- `beethoven_hardware()` runs `sbt runMain` with `BEETHOVEN_PATH` set to the local build directory
- Generated files (Verilog, `beethoven_hardware.{h,cc}`) stay in `build/beethoven_<target>/`
- `beethoven_testbench()` links the generated C++ files and verilates/compiles the Verilog
- Each project is self-contained with no global state pollution

### Environment Variables
- `BEETHOVEN_HARDWARE_PATH`: Path to Beethoven-Hardware (auto-detected if not set)
- Simulator-specific: `VCS_HOME` (for VCS backend)

### Legacy Build (Pre-generated Hardware)
For projects using pre-generated hardware files:
```cmake
find_package(beethoven REQUIRED)
beethoven_build(my_test SOURCES my_test.cc)  # Requires BEETHOVEN_PATH env var
```

## Testing

Software tests (after building runtime):
```bash
cd Beethoven-Software
make test           # Build test executables
./bin/merge_sort    # Run specific test
./bin/alloc_sizes
```

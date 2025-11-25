---
id: overview
title: Hardware Overview
sidebar_label: Overview
---

# Beethoven Hardware Stack

A design of an accelerator is broken down into two parts.
First, there is the functional unit implementation, the core.
You would typically implement this in your HDL of choice.
We are huge fans of [Chisel HDL](https://www.chisel-lang.org), but we do understand the necessity of [System]Verilog,
so we have added [various utilities](/docs/hardware/verilog) to make it easier to integrate external Verilog modules into your design.

Second, there is the [accelerator configuration](/docs/hardware/configuration).
The configuration informs Beethoven _how_ to build your accelerator:
- What cores do you want in your design?
- How many of each?
- How are they connected to memory?

## Architecture Overview

<!-- TODO: Add architecture diagram showing Host ↔ Accelerator Core(s) ↔ DRAM with command/response interface and memory channels -->

Beethoven accelerators consist of:

- **Accelerator Cores**: Your computation logic (Chisel or Verilog)
- **BeethovenIO**: Host-accelerator command/response interface
- **Memory Channels**: High-level abstractions for DRAM access (readers, writers, scratchpads)
- **Multi-Core Topology**: Optional inter-core communication for complex pipelines

The framework handles protocol compliance (AXI, TileLink), memory controller integration, and platform-specific details, letting you focus on your algorithm.

## Design Workflow

1. **Implement your core logic** in Chisel or Verilog
2. **Define host interface** using `BeethovenIO` with `AccelCommand`/`AccelResponse`
3. **Configure memory interfaces** (read/write channels, scratchpads, or manual memory)
4. **Specify build configuration** (number of cores, memory topology)
5. **Build and simulate** using `BuildMode.Simulation`
6. **Deploy to platform** using `BuildMode.Synthesis`

See the [Vector Addition Example](/docs/hardware/example) for a complete walkthrough.

## Key Abstractions

| Abstraction | Purpose |
|-------------|---------|
| **AcceleratorCore** | Top-level module for your computation logic |
| **BeethovenIO** | Host-accelerator interface (command/response) |
| **ReadChannelConfig / WriteChannelConfig** | Off-chip DRAM streaming with automatic DMA |
| **ScratchpadConfig** | On-chip buffering with automatic init/writeback |
| **Memory** | User-managed on-chip memory (BRAM/URAM/SRAM) |
| **AcceleratorConfig** | Build configuration (cores, memory, topology) |
| **BeethovenBuild** | Build entry point (platform, synthesis/simulation) |

## Next Steps

### Core Topics

- **[Illustrative Example](/docs/hardware/example)** - Complete vector addition walkthrough
- **[Memory Interfaces](/docs/hardware/memory)** - Read/write channels, scratchpads, user-managed memory
- **[Host Interface](/docs/hardware/host-interface)** - BeethovenIO, AccelCommand, AccelResponse
- **[Configuration & Build](/docs/hardware/configuration)** - AcceleratorConfig, platforms, build modes

### Advanced Topics

- **[Verilog Integration](/docs/hardware/verilog)** - Integrate external Verilog modules
- **[Cross-Core Communication](/docs/hardware/cross-core)** - Multi-core topologies and inter-core data flow
- **[ASIC Memory Compiler](/docs/hardware/asic-memory-compiler)** - ASIC SRAM instantiation

### Platform Deployment

- **[Kria KV260](/docs/platforms/kria)** - Zynq Ultrascale+ deployment
- **[AWS F2](/docs/platforms/aws-f2)** - Cloud FPGA deployment
- **[Custom Platforms](/docs/platforms/custom-platform)** - Porting to new platforms

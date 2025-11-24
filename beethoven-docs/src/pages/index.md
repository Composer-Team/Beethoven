# Getting Started with Beethoven

<p align="center">
    <img src="img/favicon.png" alt="icon" width="400" />
</p>

**Beethoven** is a flexible framework for designing and deploying heterogeneous multi-core hardware accelerators. It simplifies the development process by providing high-level abstractions for communication and platform integration while maintaining performance comparable to hand-written RTL.

## Key Features

- **Multi-Core Support**: Design and deploy multiple accelerator cores with automatic resource management
- **Platform Agnostic**: Supports multiple FPGA platforms and ASIC development
- **Memory Abstraction**: Simplified memory management through Reader/Writer interfaces
- **Software Integration**: Automatic generation of C++ bindings and runtime management
- **Flexible Communication**: Built-in support for host-to-accelerator and accelerator-to-accelerator communication

## Prerequisites

- Basic understanding of hardware accelerator design concepts
- Familiarity with Chisel Hardware Description Language
- Development environment with Chisel toolchain installed

## Performance Expectations

Based on our benchmarks:
- Comparable or better performance than HLS-generated designs
- Similar resource utilization to hand-written RTL
- Significantly reduced development time
- Successful deployment of complex systems (e.g., 23-core attention accelerator)

## Getting Started

Click [**Here**](/Beethoven/)
## Template

Please clone or fork the [**Beethoven Accelerator Template**](https://github.com/Composer-Team/beethoven-template) and start building your accelerator with Beethoven.

## Need Help Beyond the Doc?

- Submit issues on our [GitHub repository](https://github.com/Composer-Team/Beethoven-Software)
- Contact our [team members](/links/)

---
id: comparison
title: Beethoven vs Alternatives
sidebar_label: Comparison
---

# Beethoven vs Alternatives

Beethoven sits at the intersection of hardware design and software integration. Understanding how it compares to alternatives helps you choose the right tool for your project.

## Quick Comparison

| Approach | Hardware Control | SW Integration | Multi-Platform | Learning Curve |
|----------|------------------|----------------|----------------|----------------|
| **Beethoven** | Full (Chisel/Verilog) | Automatic C++ | AWS F2, Kria, Sim | Medium |
| HLS (Vitis/Intel) | Limited (C++) | Manual | Platform-specific | Low-Medium |
| OpenCL/SYCL | Very Limited | Standardized | Multi-vendor | Medium |
| Chisel (Manual) | Full | Manual | Any | Medium-High |
| Pure Verilog | Full | Manual | Any | High |

## Beethoven vs High-Level Synthesis (HLS)

### HLS (Xilinx Vitis, Intel HLS Compiler)

**What HLS Does Well:**
- Low barrier to entry (C/C++ to hardware)
- Automatic pipelining and optimization
- Integrated with vendor tools (Vivado, Quartus)
- Good for algorithm exploration

**Where Beethoven Excels:**
- **Hardware Control**: Full access to Chisel primitives, custom protocols, and timing
- **Multi-Platform**: Single design targets AWS F2, Kria, simulation without vendor lock-in
- **Software Integration**: Automatic C++ bindings match your hardware interface exactly
- **Composability**: Modular hardware with type-safe protocol negotiation (Diplomacy)
- **Customization**: Define custom memory interfaces, not limited to vendor templates

**When to Use HLS:**
- Rapid prototyping from existing C++ algorithms
- Team lacks hardware design experience
- Vendor-specific optimizations are critical

**When to Use Beethoven:**
- Need precise control over microarchitecture
- Deploying across multiple FPGA platforms
- Building complex multi-core accelerators
- Integrating custom protocols or interfaces

### Example: Matrix Multiply

<table>
<tr>
<th>Vitis HLS</th>
<th>Beethoven (Chisel)</th>
</tr>
<tr>
<td>

```cpp
void matmul(
  int A[N][N],
  int B[N][N],
  int C[N][N]
) {
#pragma HLS INTERFACE m_axi port=A
#pragma HLS INTERFACE m_axi port=B
#pragma HLS INTERFACE m_axi port=C
  for(int i=0; i<N; i++)
    for(int j=0; j<N; j++)
      for(int k=0; k<N; k++)
        C[i][j] += A[i][k]*B[k][j];
}
```

</td>
<td>

```scala
class MatMul(implicit p: Parameters)
  extends AcceleratorCore {
  val io = BeethovenIO(
    new AccelCommand("matmul") {
      val a_addr = Address()
      val b_addr = Address()
      val c_addr = Address()
      val n = UInt(32.W)
    },
    EmptyAccelResponse()
  )

  val a_reader = getReaderModule("a")
  val b_reader = getReaderModule("b")
  val c_writer = getWriterModule("c")

  // Full control over datapath
  // Custom memory access patterns
  // Explicit parallelism
}
```

</td>
</tr>
</table>

**Trade-offs:**
- HLS: Faster to write, less control, vendor-specific
- Beethoven: More verbose, full control, portable

---

## Beethoven vs OpenCL/SYCL

### OpenCL for FPGAs (Intel FPGA SDK, Xilinx Vitis)

**What OpenCL Does Well:**
- Standardized API across CPU/GPU/FPGA
- Abstract hardware details from application developer
- Good for heterogeneous computing workflows

**Where Beethoven Excels:**
- **No Runtime Overhead**: Direct hardware calls, no OpenCL runtime
- **Custom Interfaces**: Not limited to OpenCL memory model
- **Explicit Control**: Specify memory channels, scratchpads, communication topology
- **Simulation**: Fast co-simulation without vendor tools
- **Lower Latency**: ~10µs command latency vs OpenCL's millisecond overhead

**When to Use OpenCL:**
- Portability across CPU/GPU/FPGA is critical
- Team already uses OpenCL for GPU acceleration
- Need mature ecosystem (libraries, debuggers)

**When to Use Beethoven:**
- Latency-sensitive applications (microsecond response times)
- Custom hardware architectures (scratchpads, custom interconnect)
- Tight integration with host application
- Don't need GPU/CPU portability

---

## Beethoven vs Raw Chisel

### Chisel with Manual Integration

**What Raw Chisel Gives You:**
- Full hardware expressiveness
- Same Chisel benefits (type safety, generators)
- Freedom to structure integration

**What Beethoven Adds:**
- **Automatic C++ Bindings**: No manual command encoding
- **Memory Abstractions**: Readers, Writers, Scratchpads with automatic protocol generation
- **Multi-Platform Support**: Platform abstraction (AWS F2, Kria, Simulation)
- **Co-Simulation Infrastructure**: Verilator/VCS/Icarus integration out-of-the-box
- **Floorplanning**: Automatic SLR partitioning for multi-die FPGAs

**When to Use Raw Chisel:**
- Building non-accelerator hardware (processors, peripherals, ASICs)
- Full control over build flow and integration
- Custom simulator or FPGA platform not supported by Beethoven

**When to Use Beethoven:**
- Building host-accelerator systems
- Need fast iteration (automatic software generation)
- Targeting supported platforms (AWS F2, Kria)
- Want turnkey simulation environment

---

## Beethoven vs Pure Verilog/SystemVerilog

### Manual Verilog Development

**What Verilog Gives You:**
- Maximum hardware control
- Industry-standard language
- Universal tool support

**What Beethoven Adds:**
- **Generator Power**: Parameterized modules with Scala metaprogramming
- **Type Safety**: Compile-time checking of connections and protocols
- **Automatic C++ Bindings**: No manual register map or command encoding
- **Platform Abstraction**: Same design runs on AWS F2, Kria, simulation
- **Faster Development**: Less boilerplate, automatic interconnect generation

**When to Use Verilog:**
- Team lacks Scala/Chisel experience and unwilling to learn
- Need industry-standard language for IP delivery
- Working with legacy Verilog codebase

**When to Use Beethoven:**
- Building new accelerators from scratch
- Want hardware generators (parameterized designs)
- Need fast software integration
- Targeting multiple platforms

:::note Verilog Integration
Beethoven supports Verilog via Chisel [Blackboxes](https://www.chisel-lang.org/docs/explanations/blackboxes). You can integrate existing Verilog IP into Beethoven accelerators.
:::

---

## Comparison Matrix

### Design Productivity

| Feature | Beethoven | HLS | OpenCL | Raw Chisel | Verilog |
|---------|-----------|-----|--------|------------|---------|
| Time to First Working Design | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Hardware Expressiveness | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Software Integration Effort | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ |
| Multi-Platform Support | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Simulation Speed | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### Performance Characteristics

| Metric | Beethoven | HLS | OpenCL | Notes |
|--------|-----------|-----|--------|-------|
| Command Latency | ~10µs | ~10µs | ~1ms | OpenCL has runtime overhead |
| Peak Throughput | Hardware-limited | Hardware-limited | Hardware-limited | All reach same peak if tuned |
| Resource Utilization | Excellent (manual control) | Good (auto-optimized) | Good | HLS may over-provision |
| Power Efficiency | Excellent | Good | Good | Manual designs typically more efficient |

---

## Decision Guide

### Choose Beethoven if you:
- ✅ Need precise control over hardware microarchitecture
- ✅ Are building custom accelerators for compute-intensive tasks
- ✅ Want automatic C++ integration without manual register maps
- ✅ Need to support multiple FPGA platforms (AWS F2, Kria)
- ✅ Have (or want to learn) Chisel/Scala experience
- ✅ Value fast co-simulation for debugging
- ✅ Are comfortable with hardware-software co-design

### Choose HLS if you:
- ✅ Have existing C++ algorithms to accelerate
- ✅ Team has limited hardware design experience
- ✅ Need rapid prototyping and iteration
- ✅ Vendor-specific optimizations are acceptable
- ✅ Don't need multi-platform portability

### Choose OpenCL if you:
- ✅ Need portability across CPU/GPU/FPGA
- ✅ Already use OpenCL for GPU acceleration
- ✅ Can tolerate millisecond command latencies
- ✅ Prefer standardized APIs over custom integration

### Choose Raw Chisel if you:
- ✅ Building non-accelerator hardware (ASICs, processors)
- ✅ Need custom build flows or unsupported platforms
- ✅ Don't need automatic software generation
- ✅ Want maximum flexibility in integration

### Choose Verilog if you:
- ✅ Team is Verilog-only and unwilling to adopt new tools
- ✅ Need industry-standard IP delivery format
- ✅ Working with large legacy Verilog codebase

---

## Hybrid Approaches

Beethoven is not mutually exclusive with other approaches:

**Beethoven + Verilog:**
- Use Chisel Blackboxes to integrate Verilog IP
- Best of both worlds: generator power + existing IP

**Beethoven + HLS:**
- Use HLS to generate compute kernels (Verilog output)
- Wrap HLS kernels in Beethoven infrastructure for multi-platform support

**Beethoven + OpenCL:**
- OpenCL for GPU/CPU path, Beethoven for FPGA path
- Shared high-level application logic

---

## Getting Started

If Beethoven sounds like the right fit, start here:
- [Getting Started Guide](/docs/getting-started) - Setup and first accelerator
- [Vector Addition Example](/docs/hardware/example) - Complete walkthrough
- [Hardware Overview](/docs/hardware/overview) - Architecture and design patterns

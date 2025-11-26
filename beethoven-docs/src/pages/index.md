# Beethoven

<p align="center">
    <img src="img/favicon.png" alt="icon" width="400" />
</p>

<p align="center" style="font-size: 1.5em; font-weight: 500; margin-top: 1em;">
Hardware acceleration for FPGA and ASIC, simplified
</p>

---

## What is Beethoven?

Beethoven is **CUDA for FPGA/ASIC** - a complete framework that makes hardware acceleration accessible. Write your accelerator in Chisel, and Beethoven handles the rest: automatic C++ bindings, multi-platform deployment, memory management, and runtime infrastructure.

**Design once. Deploy everywhere.** From simulation to AWS F2 to Xilinx Kria to custom ASICs.

---

## Why Beethoven?

Traditional FPGA/ASIC development is painful. You write RTL, manually create register maps, wire up memory controllers, build platform-specific shells, write custom drivers, and pray it all works. **Beethoven eliminates this drudgery.**

| Without Beethoven | With Beethoven |
|-------------------|----------------|
| ❌ Manual C++ bindings and register maps | ✅ Automatic C++ interface generation |
| ❌ Platform-specific memory controllers | ✅ Unified Reader/Writer abstractions |
| ❌ Custom shell integration for each FPGA | ✅ One design, multiple platforms |
| ❌ Separate simulation and FPGA codebases | ✅ Same software binary in simulation and hardware |
| ❌ Weeks to integrate new accelerators | ✅ Hours to working prototype |

---

## Quick Start

**1. Clone the template:**
```bash
git clone https://github.com/Composer-Team/beethoven-template
cd beethoven-template
```

**2. Define your accelerator:**
```scala
class MyAccelerator(implicit p: Parameters) extends AcceleratorCore {
  val io = BeethovenIO(
    new AccelCommand("process") { val addr = Address() },
    EmptyAccelResponse()
  )
  val reader = getReaderModule("input")
  val writer = getWriterModule("output")
  // Your logic here
}
```

**3. Build and simulate:**
```bash
sbt run  # Generate hardware
cd Beethoven-Runtime && make sim_icarus
cd ../testbench && make && ./my_test
```

**4. Deploy to FPGA:**
Change one line (`platform = new KriaPlatform`) and rebuild. Same design now runs on real hardware.

[**→ Full Getting Started Guide**](/docs/getting-started)

---

## Key Features

### 🚀 **Automatic Software Integration**
Your `BeethovenIO` interface becomes a type-safe C++ function. No manual command encoding, no register maps, no guesswork.

```scala
// Hardware (Chisel)
BeethovenIO(new AccelCommand("matmul") {
  val a_addr = Address()
  val b_addr = Address()
  val n = UInt(32.W)
})
```

```cpp
// Generated C++ (automatic)
namespace MyCore {
  response_handle<bool> matmul(
    uint16_t core_id,
    remote_ptr a_addr,
    remote_ptr b_addr,
    uint32_t n
  );
}
```

### 🌍 **Multi-Platform Deployment**
Write once, deploy anywhere. Beethoven abstracts platform details:
- **AWS F2/F1**: 3-die cloud FPGAs with automatic AFI generation
- **Xilinx Kria**: Embedded Zynq UltraScale+ boards
- **Xilinx U200**: Data center accelerator cards
- **Simulation**: Verilator, VCS, Icarus Verilog
- **Custom Platforms**: Define your own (ASIC, custom FPGA)

### 💾 **Memory Made Simple**
Forget AXI4 protocol specs. Request memory interfaces by name:

```scala
val reader = getReaderModule("input_data")
val writer = getWriterModule("output_data")

reader.requestChannel.bits.addr := my_address
reader.requestChannel.bits.len := num_bytes
// Data automatically streams on reader.dataChannel
```

Beethoven generates DMA engines, handles protocol conversion, and manages physical memory channels.

### 🏗️ **Multi-Core Architectures**
Build complex heterogeneous systems with multiple accelerator types:
- Automatic resource allocation across cores
- Core-to-core communication topology
- Platform-aware placement and floorplanning

Example: 23-core transformer attention accelerator deployed on AWS F2.

### 🔧 **Full Hardware Control**
Beethoven doesn't hide hardware complexity - it manages it. You still write Chisel (or Verilog via blackboxes), with full access to:
- Custom datapaths and pipelines
- Scratchpads and on-chip memory
- Multi-die floorplanning (SLR partitioning)
- Clock domain crossings
- Custom protocols

---

## Proven at Scale

Beethoven has been used to build and deploy:
- **23-core transformer attention accelerator** on AWS F2
- **Multi-die floorplanned designs** across 3 SLRs
- **High-throughput DMA engines** saturating 512-bit memory interfaces
- **Heterogeneous accelerator topologies** with core-to-core communication

Performance comparable to hand-written RTL. Development time measured in days, not months.

---

## How It Works

1. **Define your hardware** in Chisel using `AcceleratorCore`
2. **Specify interfaces** with `BeethovenIO` (host commands) and memory channels
3. **Configure your build** with target platform and build mode
4. **Beethoven generates:**
   - Synthesizable Verilog RTL
   - Type-safe C++ bindings matching your interface
   - Memory controllers and DMA engines
   - Platform-specific integration (shells, constraints)
5. **Write testbench** using generated C++ API
6. **Simulate** with Verilator/VCS/Icarus
7. **Deploy** to FPGA or ASIC with platform-specific flow

[**→ See Complete Example**](/docs/hardware/example)

---

## Who Should Use Beethoven?

✅ **You want hardware-level performance** but don't want to spend weeks on integration boilerplate

✅ **You need multi-platform support** (cloud FPGAs, embedded boards, custom ASICs)

✅ **You're building custom accelerators** where HLS doesn't give you enough control

✅ **You value fast iteration** with co-simulation and automatic software generation

❌ **You need a GUI-based design tool** (Beethoven is code-first)

❌ **Your team can't learn Chisel/Scala** (though we provide templates and examples)

---

## Compare Beethoven

| | Beethoven | HLS (Vitis) | OpenCL | Raw Chisel |
|-|-----------|-------------|--------|------------|
| **Hardware Control** | Full | Limited | Very Limited | Full |
| **SW Integration** | Automatic | Manual | Standardized | Manual |
| **Multi-Platform** | ✅ | ❌ | ✅ | ❌ |
| **Learning Curve** | Medium | Low-Medium | Medium | Medium-High |
| **Latency** | ~10µs | ~10µs | ~1ms | ~10µs |

[**→ Detailed Comparison**](/docs/comparison)

---

## Get Started Now

### 📚 **New to Beethoven?**
Start with the [Getting Started Guide](/docs/getting-started) and [Vector Addition Example](/docs/hardware/example).

### 🎯 **Specific Use Case?**
- [Multi-die FPGAs](/docs/hardware/floorplanning) - SLR partitioning and floorplanning
- [AWS F2 Deployment](/docs/platforms/aws-f2) - Cloud FPGA acceleration
- [Embedded Systems](/docs/platforms/kria) - Xilinx Kria/Zynq boards
- [Debugging](/docs/hardware/debugging) - Simulation and FPGA debugging

### 🛠️ **Ready to Build?**
Clone the [Beethoven Template](https://github.com/Composer-Team/beethoven-template) and start coding.

---

## Learn More

### 🎓 **Conference Tutorials**
Hands-on workshops and tutorials from conferences where Beethoven has been presented.
- [Conference Tutorials Page](/tutorials) - Workshop materials and presentations

### 📄 **Research & Publications**
Read peer-reviewed research on Beethoven's architecture and performance.
- [ISPASS 2025 Paper](/papers) - Framework design and evaluation
- [All Publications](/papers) - Conference papers and technical reports

---

## Community & Support

- **Issues & Bugs**: [GitHub Issues](https://github.com/Composer-Team/Beethoven-Software/issues)
- **Questions**: [Team Contacts](/links/)
- **Template**: [Beethoven Accelerator Template](https://github.com/Composer-Team/beethoven-template)

---

<p align="center" style="margin-top: 2em; font-style: italic;">
Hardware acceleration shouldn't be this hard. Beethoven makes it simple.
</p>

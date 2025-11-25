---
id: asic-memory-compiler
title: ASIC Memory Compiler
sidebar_label: ASIC Memory Compiler
---

# ASIC Memory Compiler Support

## Why Memory Compiler Abstraction?

When moving from FPGA to ASIC, memory implementation changes fundamentally. FPGAs provide fixed BRAM/URAM primitives that work identically across designs, but ASIC flows require integrating with foundry-specific memory compilers that generate custom SRAM macros. Each foundry (TSMC, GlobalFoundries, Samsung, etc.) and each process node has different:

- Available SRAM configurations (row/column combinations)
- Port options (single-port, dual-port, multi-port)
- Signal naming and polarity conventions
- Timing characteristics across process corners
- Deliverable formats (GDS, LEF, Verilog models, Liberty files)

Beethoven abstracts these differences behind the `MemoryCompiler` interface, allowing your accelerator design to remain unchanged while swapping the underlying ASIC process.

## Implementing Your Memory Compiler

To integrate your foundry's memory compiler, extend the `MemoryCompiler` abstract class:

```scala
abstract class MemoryCompiler {
  val mostPortsSupported: Int
  val isActiveHighSignals: Boolean
  val supports_onlyPow2: Boolean
  val supportedCorners: Seq[String]
  val deliverablesSupported: Seq[MemoryCompilerDeliverable]

  def generateMemoryFactory(char_t: sramChar_t)(implicit p: Parameters):
    () => BaseModule with HasMemoryInterface

  def isLegalConfiguration(char_t: sramChar_t): Boolean

  def getFeasibleConfigurations(
    rows: Int, cols: Int, ports: Int, withWriteEnable: Boolean
  ): Seq[sramChar_t]
}
```

### What Each Field Represents

**`mostPortsSupported`**: Memory compilers offer different port configurations. Single-port SRAMs are smaller but require arbitration for concurrent access. Dual-port SRAMs allow simultaneous read/write but cost more area. Your compiler should report the maximum port count it can generate.

**`isActiveHighSignals`**: Different memory macros use different signal polarities. Some use active-high chip select (CS=1 to enable), others use active-low (CS_N=0 to enable). Beethoven uses this flag to generate the correct polarity conversion logic so your RTL doesn't need to change per-process.

**`supports_onlyPow2`**: Some memory compilers only generate power-of-2 dimensions (e.g., 256x32, 512x64) for physical layout efficiency. When true, Beethoven pads memory requests to the next power of 2.

**`supportedCorners`**: For timing closure, you need SRAM timing across process corners (Fast-Fast, Typical-Typical, Slow-Slow). The compiler reads datasheet files for each corner and uses the worst-case timing for conservative synthesis.

### The Memory Interface Contract

All memory macros must implement `HasMemoryInterface`:

```scala
trait HasMemoryInterface {
  def data_in: Seq[UInt]
  def data_out: Seq[UInt]
  def addr: Seq[UInt]
  def chip_select: Seq[Bool]
  def read_enable: Seq[Bool]
  def write_enable: Seq[UInt]
  def clocks: Seq[Bool]
}
```

This standardized interface means Beethoven can wire up any compliant SRAM macro without knowing its internal implementation. Your blackbox wrapper translates between this interface and your memory compiler's actual port names.

## Memory Cascading: Building Large Memories from Small Macros

Memory compilers don't offer every possible configuration. You might need a 2048x64 memory, but your compiler only offers 512x64 and 1024x64 macros. Beethoven solves this through cascading - automatically composing larger memories from smaller macros.

The cascading algorithm considers **latency stages**. A latency-2 memory pipeline looks like:

```
Request → [SRAM Stage 2] → [SRAM Stage 1] → [SRAM Stage 0] → Response
              ↓                  ↓                  ↓
          Registers          Registers          Registers
```

Why stages? Single-cycle memories may not meet timing at high frequencies. By splitting across pipeline stages, each stage uses a smaller, faster SRAM macro that meets the target cycle time. The `buildSRAM()` function tries increasingly aggressive configurations:

1. Try a single SRAM at full latency
2. If timing fails, split into multiple latency stages
3. If no valid SRAM exists at any latency, fall back to registers (if allowed)

## Timing-Driven Configuration Selection

When multiple SRAM configurations can satisfy your requirements, Beethoven selects based on timing and area:

```scala
val maxTcyc = 1000.0 / freqMHz  // Your target cycle time

// Only consider configurations that meet timing
val validConfigs = feasibleConfigs.filter { config =>
  config(SRAMCycleTime) < maxTcyc
}

// Among valid options, pick smallest area
val selected = validConfigs.minBy(_(SRAMArea))
```

This ensures your design meets frequency targets while minimizing silicon area. The timing data comes from datasheet files your memory compiler generates - Beethoven parses these to extract cycle time, area, and power metrics.

## Configuration Parameters

Control memory generation through CDE `Field` objects in your platform configuration:

| Field | Purpose |
|-------|---------|
| `SRAMRows` | Depth (number of addresses) |
| `SRAMColumns` | Width (bits per entry) |
| `SRAMPorts` | Port count (1=single-port, 2=dual-port) |
| `SRAMWriteEnable` | Enable per-byte write masking |

Paths to memory compiler deliverables:

| Field | Contents |
|-------|----------|
| `SRAMDatasheetPaths` | Timing/power specs for configuration selection |
| `SRAMVerilogPaths` | Behavioral models for simulation |
| `SRAMGDSPaths` | Physical layouts for place-and-route |
| `SRAMLEFPaths` | Abstract views for P&R tools |
| `SRAMLibPaths` | Liberty timing for synthesis |

## Example: Integrating a Custom Process

Here's a skeleton for integrating your foundry's memory compiler:

```scala
class MyFoundryMemoryCompiler extends MemoryCompiler {
  // Our compiler generates single and dual-port SRAMs
  override val mostPortsSupported = 2

  // Our macros use active-high chip select
  override val isActiveHighSignals = true

  // We support arbitrary dimensions
  override val supports_onlyPow2 = false

  // We have timing data for these corners
  override val supportedCorners = Seq("ff_0p99v_m40c", "tt_0p90v_25c", "ss_0p81v_125c")

  // Available configurations from our memory compiler
  // Map: port count -> list of (columns, rows)
  val catalog: Map[Int, Seq[(Int, Int)]] = Map(
    1 -> Seq((32, 256), (32, 512), (64, 256), (64, 512), (128, 256)),
    2 -> Seq((32, 128), (32, 256), (64, 128))
  )

  override def generateMemoryFactory(char_t: sramChar_t)(implicit p: Parameters) = {
    // Return a factory that instantiates your blackbox wrapper
    () => new MyFoundrySRAMWrapper(char_t.rows, char_t.cols, char_t.ports)
  }

  override def isLegalConfiguration(char_t: sramChar_t) = {
    catalog.get(char_t.ports).exists(_.contains((char_t.cols, char_t.rows)))
  }

  override def getFeasibleConfigurations(rows: Int, cols: Int, ports: Int, withWE: Boolean) = {
    // Return all catalog entries that can satisfy the request
    catalog.getOrElse(ports, Seq.empty)
      .filter { case (c, r) => c >= cols && r >= rows }
      .map { case (c, r) => sramChar_t(ports, r, c, withWE) }
  }
}
```

Then register it with your platform:

```scala
class MyASICPlatform extends Platform with HasMemoryCompiler {
  override val platformType = PlatformType.ASIC
  override val memoryCompiler = new MyFoundryMemoryCompiler
  override val clockRateMHz = 500  // Target frequency for timing selection
}
```

## When Things Don't Fit

If your design requests a memory that can't be satisfied:

1. **Too large**: Beethoven cascades multiple smaller macros (adding latency)
2. **Port mismatch**: Falls back to lower port count with arbitration logic
3. **No valid config**: Uses register-based memory if `allowFallbackToRegisters` is true
4. **Still can't fit**: Raises a configuration error at elaboration time

The fallback to registers is useful for very small memories (< 64 entries) where SRAM macro overhead isn't worth it.

## Related Documentation

- [Hardware Stack Overview](/docs/hardware/overview) - Using memory in accelerator designs
- [New Platform Guide](/docs/platforms/custom-platform) - Full platform integration including memory compiler registration

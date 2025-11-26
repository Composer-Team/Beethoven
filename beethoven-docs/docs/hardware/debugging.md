---
id: debugging
title: Debugging Guide
sidebar_label: Debugging
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Debugging Guide

Debugging hardware accelerators requires different strategies for simulation versus FPGA deployment. This guide covers the tools and techniques available in Beethoven for finding and fixing issues at each stage.

## Simulation Debugging

### Waveform Generation

Beethoven's simulation backends automatically generate waveforms for debugging. The simulator type determines the waveform format:

<Tabs>
<TabItem value="verilator" label="Verilator" default>

```bash title="Run Verilator with waveforms"
cd Beethoven-Runtime/build
cmake .. -DTARGET=sim -DSIMULATOR=verilator
make -j
./BeethovenRuntime
```

Verilator generates `dump.vcd` in the working directory. View with GTKWave:
```bash
gtkwave dump.vcd
```

:::note VCD File Size
VCD files can grow very large for long simulations. Consider limiting simulation time or using selective signal dumping.
:::

</TabItem>
<TabItem value="vcs" label="VCS">

```bash title="Run VCS with waveforms"
cd Beethoven-Runtime/build
cmake .. -DTARGET=sim -DSIMULATOR=vcs
make -j
../scripts/build_vcs.sh
./BeethovenTop
```

VCS generates FSDB or VPD waveforms. Always use the `finish` command to properly flush waveforms:
```tcl
# In VCS shell after CTRL+C
finish
```

:::warning Waveform Corruption
Never kill VCS with SIGKILL. Always use `finish` to ensure waveform files are properly written.
:::

</TabItem>
<TabItem value="icarus" label="Icarus Verilog">

```bash title="Run Icarus Verilog"
cd Beethoven-Runtime
make sim_icarus
```

Icarus generates VCD waveforms. Use `finish` to properly close:
```bash
# After CTRL+C
finish
```

</TabItem>
</Tabs>

### Signal Tracing Best Practices

1. **Start Narrow**: Only trace signals in suspect modules initially
2. **Use Hierarchy**: Navigate module hierarchy in waveform viewer to find signals
3. **Add Markers**: Mark cycle boundaries and key events (command issue, response return)
4. **Compare Expected vs Actual**: Run reference implementation alongside accelerator
5. **Check Handshakes**: Verify `valid`/`ready` protocol compliance on all interfaces

### Memory Debugging

Beethoven integrates **DRAMsim3** for cycle-accurate DRAM simulation. To debug memory timing issues:

```bash title="Configure DRAM model"
# VPI-based simulators (VCS, Icarus)
cmake .. -DDRAMSIM_CONFIG=DDR4_8Gb_x16_3200.ini

# Verilator
./BeethovenRuntime -dramconfig DDR4_8Gb_x16_3200.ini
```

DRAMsim3 configurations available:
- `DDR4_8Gb_x16_3200.ini` - Default (3200 MT/s)
- `DDR4_8Gb_x8_2400.ini` - Slower DDR4 (2400 MT/s)
- `DDR3_8Gb_x8_1600.ini` - DDR3 variant

:::tip Memory Bottleneck Detection
If your accelerator performs well in simulation but poorly on FPGA, try slower DRAMsim3 configs to identify memory bottlenecks.
:::

## Software/Hardware Co-Debugging

### Using Printf Debugging

Add debug prints to your testbench to correlate with waveform events:

```cpp title="Testbench with timing markers"
#include <iostream>
#include <chrono>

auto start = std::chrono::steady_clock::now();

auto resp = myCore::process(0, input_ptr);
std::cout << "[T+" << std::chrono::duration_cast<std::chrono::microseconds>(
  std::chrono::steady_clock::now() - start).count()
  << "µs] Command issued\n";

auto result = resp.get();
std::cout << "[T+" << std::chrono::duration_cast<std::chrono::microseconds>(
  std::chrono::steady_clock::now() - start).count()
  << "µs] Response received\n";
```

Search for these timestamps in your waveform to quickly locate events.

### Response Timeouts

If responses never arrive, check:

1. **Protocol Compliance**: Ensure `req.ready` is high when accepting commands
2. **Response Valid**: Verify `resp.valid` is driven high after processing
3. **Deadlock**: Check for circular dependencies in module state machines
4. **Memory Initialization**: Verify scratchpads are initialized before use

```cpp title="Detect response timeouts"
auto resp = myCore::process(0, ptr);
auto result = resp.try_get();

if (!result.has_value()) {
    std::cerr << "Response not ready - accelerator may be stalled\n";
    // Check waveform for state machine or memory issues
}
```

## FPGA Debugging

### Build Failures

When synthesis or place-and-route fails:

**1. Check Timing Reports**
```bash
# Kria/Vivado
vivado post_route.dcp
report_timing_summary
```

Look for:
- Negative slack (timing violations)
- High fanout nets
- SLR crossing violations on multi-die FPGAs

**2. Resource Utilization**
```tcl
# In Vivado
report_utilization
```

Check if you've exceeded:
- LUTs, FFs, BRAMs, URAMs
- DSP blocks
- Clock regions (for Kria)

**3. AWS F2 AFI Build Failures**

AWS stores detailed build logs in S3:
```bash
aws s3 cp s3://<your-bucket>/<logs-folder>/ . --recursive
```

Common issues:
- Routing congestion → Reduce design size or improve floorplanning
- Timing closure → Lower clock frequency or pipeline critical paths
- Resource exhaustion → Check utilization per SLR

:::danger Silent Failures
AWS AFI builds may report success but produce non-functional AFIs. Always test with a known-good workload after loading.
:::

### Runtime Debugging on FPGA

**Limited Hardware Debugging Support:**

Beethoven does not currently integrate Vivado ILA (Integrated Logic Analyzer) or VIO (Virtual I/O) cores. For hardware debugging:

1. **Add Simulation First**: Reproduce the issue in simulation where waveforms are available
2. **Use Response Payloads**: Return debug data through `AccelResponse` payloads
3. **External Vivado Debug**: Manually insert ILA cores in generated Verilog
4. **Iterative Refinement**: Add debug outputs to your Chisel, rebuild, and redeploy

#### Inserting ILA Manually

After Beethoven generates Verilog, you can insert ILA cores:

```tcl title="Add ILA in Vivado TCL"
# In synth.tcl or during implementation
create_debug_core ila_core ila
set_property C_DATA_DEPTH 4096 [get_debug_cores ila_core]
connect_debug_port ila_core/clk [get_nets my_clock]
connect_debug_port ila_core/probe0 [get_nets {my_signal[*]}]
```

This requires re-running synthesis after Beethoven generation.

### Debug AXI Cache/Prot Signals

Some platforms support debugging AXI protocol signals. Currently only **AUPZU3Platform** has this enabled:

```scala title="Platform with debug signals"
override val hasDebugAXICACHEPROT = true
```

When enabled, the host can override AXI CACHE and PROT signal values for debugging cache coherency issues.

## Common Issues and Solutions

### Issue: Accelerator Hangs (No Response)

**Symptoms**: `resp.get()` never returns, testbench hangs

**Debug Steps**:
1. Check waveform for `resp.valid` signal - is it ever asserted?
2. Verify state machine in accelerator reaches "response" state
3. Look for deadlocks in memory interfaces (e.g., waiting for `ready` that never comes)
4. Check if command was properly decoded (inspect `req.bits` in waveform)

**Common Causes**:
- Forgot to drive `resp.valid := true.B` in response state
- Memory reader/writer stuck waiting for initialization
- Circular dependency in state machine transitions

---

### Issue: Data Corruption (Wrong Results)

**Symptoms**: Results don't match expected values

**Debug Steps**:
1. Add reference implementation in software, compare results
2. Check memory alignment - addresses must align to `dataBytes`
3. Verify `copy_to_fpga()` / `copy_from_fpga()` are called on discrete platforms
4. Inspect waveform to see actual data values on memory interfaces
5. Check for race conditions in concurrent memory accesses

**Common Causes**:
- Misaligned addresses (see [Memory Alignment](/docs/hardware/memory#alignment-requirements))
- Forgot to call `copy_to_fpga()` before accelerator execution
- Endianness mismatch between host and accelerator
- Off-by-one errors in address calculation

---

### Issue: Timing Violations (Won't Meet Timing)

**Symptoms**: Post-route timing report shows negative slack

**Debug Steps**:
1. Identify critical path in timing report
2. Check if path crosses SLRs (multi-die FPGAs)
3. Look for high-fanout nets or long combinational chains
4. Review floorplanning constraints (are modules placed optimally?)

**Solutions**:
- Add pipeline stages on critical paths
- Use `RegNext()` to break combinational chains
- Improve SLR placement for multi-die FPGAs
- Reduce clock frequency if architecture can't meet timing
- Use `LazyModuleWithFloorplan` to control placement

---

### Issue: Simulation Works, FPGA Fails

**Symptoms**: Perfect behavior in Verilator/VCS, failures on real hardware

**Debug Steps**:
1. Test with more realistic DRAM model (slower DRAMsim3 config)
2. Check for uninitialized registers (simulation often defaults to 0)
3. Look for metastability issues (clock domain crossings)
4. Verify reset behavior (reset may take longer on FPGA)

**Common Causes**:
- Insufficient DRAM bandwidth (simulation DRAM is often unrealistic)
- Uninitialized `Reg()` - always use `RegInit()`
- Clock domain crossing without proper synchronization
- Race conditions exposed by different timing on FPGA

---

### Issue: Build Takes Forever

**Symptoms**: Vivado synthesis/P&R runs for hours

**Solutions**:
- Enable incremental compilation in Vivado
- Use hierarchical synthesis for large designs
- Simplify floorplanning constraints (over-constraining slows P&R)
- For AWS F2: Use smaller instance types for builds (c5.4xlarge is usually sufficient)

## Debugging Checklist

Before filing a bug report or asking for help:

- [ ] Reproduced in simulation with waveforms
- [ ] Checked protocol compliance on all `BeethovenIO` interfaces
- [ ] Verified memory alignment (address and length align to `dataBytes`)
- [ ] Confirmed `copy_to_fpga()` / `copy_from_fpga()` are called
- [ ] Reviewed generated `beethoven_hardware.h` matches expectations
- [ ] Tested with reference software implementation
- [ ] Checked timing reports (FPGA builds only)
- [ ] Verified resource utilization is within limits

## See Also

- [Memory Interfaces](/docs/hardware/memory) - Alignment and protocol requirements
- [Host Interface](/docs/hardware/host-interface) - Command/response protocol
- [Example](/docs/hardware/example) - Complete working example with state machine
- [Floorplanning](/docs/hardware/floorplanning) - Multi-die timing optimization

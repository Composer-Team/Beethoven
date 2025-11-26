---
id: floorplanning
title: Multi-Die Floorplanning
sidebar_label: Floorplanning
---

# Multi-Die Floorplanning

For large multi-die FPGAs (e.g., AWS F2's 3-die VU9P), Beethoven provides automated floorplanning support to partition your accelerator across Super Logic Regions (SLRs). This enables you to control placement, manage SLR crossing timing, and optimize resource utilization across dies.

:::tip When to Use Floorplanning
Use floorplanning when targeting multi-die FPGAs to control placement and improve timing closure. Single-die platforms automatically skip constraint generation.
:::

## Platform Support

Multi-die floorplanning is supported on:
- **AWS F2**: 3-die Xilinx VU9P (SLR0, SLR1, SLR2)
- **AWS F1**: 3-die Xilinx VU9P (SLR0, SLR1, SLR2)
- **Xilinx U200**: 3-die Xilinx VU+ (SLR0, SLR1, SLR2)

Single-die platforms (Kria, AUPZU3, Simulation) automatically disable floorplanning constraints.

## Physical Device Topology

Platforms declare their physical topology using `DeviceConfig`, which defines SLR boundaries and resources:

```scala title="AWS F2 platform topology"
override val physicalDevices = List(
  DeviceConfig(0, "pblock_CL_SLR0"),
  DeviceConfig(1, "pblock_CL_SLR1"),
  DeviceConfig(2, "pblock_CL_SLR2")
)

// Resource budgets per SLR
override val nURAMs: Map[Int, Int] = Map((0, 230), (1, 204), (2, 256))
override val nBRAMs: Map[Int, Int] = Map((0, 480), (1, 412), (2, 537))

// Die connectivity (which SLRs are adjacent)
override val physicalConnectivity = List((0,1), (1,2))
```

## Placing Modules on SLRs

Use `DeviceContext.withDevice()` to specify which SLR a module should be placed on:

```scala title="Manual SLR placement"
import beethoven.Floorplanning._

class MyAccelerator(implicit p: Parameters) extends AcceleratorCore {
  // Place memory controller on SLR1
  DeviceContext.withDevice(1) {
    val memCtrl = LazyModule(new MemoryController)
  }

  // Place compute array on SLR2
  DeviceContext.withDevice(2) {
    val computeArray = LazyModule(new ComputeArray)
  }
}
```

:::warning Unassigned Modules
Modules without explicit SLR assignment will be placed by Vivado's default placer, which may result in suboptimal timing. Always assign critical modules.
:::

## Named Module Floorplanning

For better control over generated constraints, use `LazyModuleWithFloorplan` to assign both SLR and hierarchical name:

```scala title="Named floorplanning"
DeviceContext.withDevice(slr_id) {
  val module = LazyModuleWithFloorplan(
    new MyModule,
    slr_id,
    "unique_module_name"
  )
}
```

This generates more readable XDC constraints with explicit pblock names.

## Generated Constraints

Beethoven automatically generates Vivado XDC constraint files during hardware generation. For AWS F2, the generated `user_constraints.xdc` contains:

```tcl title="Generated XDC constraints"
create_pblock pblock_mymodule_SLR1
resize_pblock pblock_mymodule_SLR1 -add SLR1
add_cells_to_pblock pblock_mymodule_SLR1 [get_cells -hierarchical -filter {NAME =~ *mymodule*}]
```

These constraints are automatically applied during synthesis.

## SLR Crossing and Reset Bridges

When signals cross SLR boundaries, use `ResetBridge` to safely propagate resets across dies with configurable delay:

```scala title="Reset bridge for SLR crossing"
import beethoven.Floorplanning.ResetBridge

// Create reset bridge with 2-cycle delay
val resetBridge = Module(new ResetBridge(delayCycles = 2))
resetBridge.io.resetIn := myReset

// Use bridged reset in target SLR
DeviceContext.withDevice(target_slr) {
  val module = LazyModule(new MyModule)
  module.reset := resetBridge.io.resetOut
}
```

:::danger Metastability Risk
Always use reset bridges when crossing SLR boundaries. Direct reset propagation across dies can cause metastability issues.
:::

## Resource-Aware Placement

Each platform declares per-SLR resource budgets (URAMs, BRAMs). Beethoven uses these budgets for placement hints:

```scala title="Platform resource specification"
override val nURAMs: Map[Int, Int] = Map((0, 230), (1, 204), (2, 256))
override val nBRAMs: Map[Int, Int] = Map((0, 480), (1, 412), (2, 537))

// Placement affinity (higher = prefer placement here)
override val placementAffinity: List[(Int, Double)] = List(
  (0, 1.0),   // SLR0: standard preference
  (1, 1.0),   // SLR1: standard preference
  (2, 1.7)    // SLR2: prefer placement (largest resources)
)
```

## Physical Interface Placement

Host interfaces (MMIO) and memory interfaces must be assigned to specific SLRs based on FPGA shell constraints:

```scala title="Interface placement"
override val physicalInterfaces = List(
  PhysicalHostInterface(0),        // MMIO on SLR0
  PhysicalMemoryInterface(1, 0)    // Memory channel 0 on SLR1
)
```

This ensures generated interconnect respects physical connectivity limitations.

## Best Practices

1. **Balance Resources**: Distribute modules across SLRs to balance URAM/BRAM usage
2. **Minimize SLR Crossings**: Keep tightly-coupled modules on the same SLR to reduce crossing overhead
3. **Place Near Interfaces**: Put memory-intensive modules on the same SLR as their memory interface
4. **Use Placement Hints**: Leverage `placementAffinity` for automatic placement optimization
5. **Profile First**: Use single-SLR builds first, then partition only when needed for timing/resources

## Debugging Floorplan

Check the generated `user_constraints.xdc` in `$BEETHOVEN_PATH/build/` to verify:
- All critical modules have pblock assignments
- No conflicting SLR assignments
- pblock names match your module hierarchy

After synthesis, use Vivado's Device view to visualize actual placement:
```bash
vivado -mode gui
open_checkpoint post_route.dcp
```

## Example: Multi-SLR Accelerator

```scala title="Complete multi-SLR accelerator"
import beethoven._
import beethoven.Floorplanning._
import chipsalliance.rocketchip.config.Parameters

class MultiSLRAccelerator()(implicit p: Parameters) extends AcceleratorCore {
  // SLR0: Host interface and command processing
  val cmdInterface = BeethovenIO(
    new AccelCommand("process") { val addr = Address() },
    EmptyAccelResponse()
  )

  // SLR1: Memory controllers (close to DRAM interface)
  DeviceContext.withDevice(1) {
    val reader = getReaderModule("input_data")
    val writer = getWriterModule("output_data")
  }

  // SLR2: Compute-intensive processing (largest SLR)
  DeviceContext.withDevice(2) {
    val computeArray = LazyModuleWithFloorplan(
      new ComputeArray,
      2,
      "compute_array"
    )
  }

  // Reset bridges for SLR crossings
  val resetBridge1to2 = Module(new ResetBridge(2))
  // ... connect bridges and logic
}
```

## See Also

- [AWS F2 Platform](/docs/platforms/aws-f2) - AWS-specific floorplanning considerations
- [Custom Platforms](/docs/platforms/custom-platform) - Defining multi-die topologies
- [Configuration](/docs/hardware/configuration) - Build configuration options

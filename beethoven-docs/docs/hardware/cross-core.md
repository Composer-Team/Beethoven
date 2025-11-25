---
id: cross-core
title: Cross-Core Communication
sidebar_label: Cross-Core Communication
---

# Cross-Core Communication

## Why Cross-Core Communication?

Many accelerator workloads benefit from decomposing into multiple specialized cores: a dispatcher that distributes work, compute cores that process data, and aggregators that collect results. Without cross-core communication, you'd need to route everything through the host CPU and external memory, adding latency and wasting bandwidth on coordination traffic.

Beethoven provides two mechanisms for cores to communicate:
1. **Inter-core commands**: One core issues RoCC commands to cores in other systems
2. **Shared scratchpads**: On-chip memory that multiple cores can read/write

## Configuring Inter-Core Commands

The first step is declaring which systems can talk to each other. In your `AcceleratorSystemConfig`:

```scala
AcceleratorSystemConfig(
  nCores = 1,
  name = "Dispatcher",
  moduleConstructor = ModuleBuilder(p => new DispatcherCore()),
  canIssueCoreCommandsTo = Seq("Workers"),  // This system can send commands to Workers
),

AcceleratorSystemConfig(
  nCores = 4,
  name = "Workers",
  moduleConstructor = ModuleBuilder(p => new WorkerCore()),
  canReceiveSoftwareCommands = false  // Workers only receive commands from Dispatcher
)
```

The `canIssueCoreCommandsTo` field establishes a one-way command channel. If you need bidirectional communication, both systems must list each other.

### Using the Inter-Core Interface

Inside your core, call `getIntraSysIO` to get a command/response interface to another system:

```scala
class DispatcherCore extends AcceleratorCore {
  // Software command interface (how host talks to this core)
  val hostIO = BeethovenIO(new DispatchCommand(), EmptyAccelResponse())

  // Inter-core interface to Workers
  val workerIO = getIntraSysIO(
    "Workers",              // Target system name
    "compute",              // Command name (must match worker's BeethovenIO)
    new WorkerCommand(),    // Command type
    new WorkerResponse()    // Response type
  )
}
```

The returned `IntraCoreIO` bundle has:
- `req`: Decoupled output with payload and `target_core_idx`
- `resp`: Decoupled input for responses from the target core

### Sending Commands

To dispatch work to a specific worker core:

```scala
// State machine to send command
when(state === s_dispatch) {
  workerIO.req.valid := true.B
  workerIO.req.bits.target_core_idx := coreToDispatch  // Which worker (0 to nCores-1)
  workerIO.req.bits.payload := myCommandPayload

  when(workerIO.req.fire) {
    state := s_wait_response
  }
}

// Wait for worker to complete
when(state === s_wait_response && workerIO.resp.fire) {
  // Worker finished, process response
  state := s_idle
}
```

### Worker Core Setup

The worker core receives commands through its normal `BeethovenIO`, but with `canReceiveSoftwareCommands = false` it only gets commands from other cores:

```scala
class WorkerCore extends AcceleratorCore {
  val my_io = BeethovenIO(new WorkerCommand(), new WorkerResponse())

  // Process command...
  when(my_io.req.fire) {
    // Start computation
  }

  // Send response when done
  my_io.resp.valid := computationDone
  my_io.resp.bits := result
}
```

## Shared Scratchpads

For data exchange between cores, going through external memory adds latency. Intra-core scratchpads provide on-chip shared memory.

### Configuring Shared Memory

Add an `IntraCoreMemoryPortInConfig` to the system that owns the scratchpad:

```scala
AcceleratorSystemConfig(
  name = "Workers",
  nCores = 4,
  memoryChannelConfig = List(
    IntraCoreMemoryPortInConfig(
      name = "shared_data",
      nChannels = 1,
      portsPerChannel = 2,          // Read/write ports
      dataWidthBits = 64,
      nDatas = 1024,                // 1024 entries
      communicationDegree = CommunicationDegree.PointToPoint,
      latency = 2
    )
  )
)
```

### Communication Degrees

The `communicationDegree` controls how addresses map to cores and channels:

| Degree | Behavior | Use Case |
|--------|----------|----------|
| `PointToPoint` | Address specifies target core and channel | Directed data exchange |
| `BroadcastAllCores` | All cores see same data per channel | Shared read-only parameters |
| `BroadcastAllCoresChannels` | All cores, all channels see same data | Global shared state |
| `BroadcastAllChannels` | Single core, all channels unified | Single-writer pattern |

### Writing to Another Core's Scratchpad

The dispatcher can write data for a specific worker to consume:

```scala
// Get write port for shared scratchpad
val writePort = getIntraCoreMemoryWritePort("Workers", "shared_data")

// Write data to worker 2's scratchpad at address 0x100
writePort.valid := true.B
writePort.bits.data := dataToSend
writePort.bits.addr := 0x100.U
writePort.bits.core.get := 2.U  // Target core (when PointToPoint)
```

### Address Space Layout

Intra-core memory addresses are hierarchically structured:

```
[system_id | core_id | endpoint_id | channel_id | space_addr]
```

Use `getCommMemAddress` to construct proper addresses:

```scala
val addr = getCommMemAddress(
  sys = "Workers",
  core = targetCoreIdx,
  endpoint = "shared_data",
  channel = 0,
  spaceAddr = offset,
  shamt = 0
)
```

## Example: Dispatcher-Worker Pattern

A complete example showing dispatcher distributing vector additions to workers:

### Configuration

```scala
val config = AcceleratorConfig(
  AcceleratorSystemConfig(
    nCores = 1,
    name = "Dispatcher",
    moduleConstructor = ModuleBuilder(p => new DispatcherCore()),
    canIssueCoreCommandsTo = Seq("Workers")
  ),
  AcceleratorSystemConfig(
    nCores = numWorkers,
    name = "Workers",
    moduleConstructor = ModuleBuilder(p => new VectorAddWorker()),
    canReceiveSoftwareCommands = false,
    memoryChannelConfig = List(
      ReadChannelConfig("vec_a", ...),
      ReadChannelConfig("vec_b", ...),
      WriteChannelConfig("result", ...)
    )
  )
)
```

### Dispatcher Core

```scala
class DispatcherCore extends AcceleratorCore {
  val hostIO = BeethovenIO(new DispatchVectorAddCmd(), EmptyAccelResponse())

  val workerIO = getIntraSysIO("Workers", "vector_add",
    new VectorAddCmd(), EmptyAccelResponse())

  val workerIdx = RegInit(0.U(log2Ceil(numWorkers).W))

  when(hostIO.req.fire) {
    // Forward command to round-robin selected worker
    workerIO.req.valid := true.B
    workerIO.req.bits.target_core_idx := workerIdx
    workerIO.req.bits.payload.vec_a_addr := hostIO.req.bits.vec_a_addr
    workerIO.req.bits.payload.vec_b_addr := hostIO.req.bits.vec_b_addr
    workerIO.req.bits.payload.result_addr := hostIO.req.bits.result_addr
    workerIO.req.bits.payload.length := hostIO.req.bits.length

    workerIdx := workerIdx + 1.U  // Next worker
  }
}
```

### Worker Core

```scala
class VectorAddWorker extends AcceleratorCore {
  val my_io = BeethovenIO(new VectorAddCmd(), EmptyAccelResponse())

  val vec_a = getReaderModule("vec_a")
  val vec_b = getReaderModule("vec_b")
  val result = getWriterModule("result")

  // Perform vector addition using memory channels
  // ...
}
```

## Multi-Die Routing

For designs spanning multiple FPGA dies or chiplets, Beethoven automatically constructs routing networks that minimize inter-die traffic. The framework uses a tree-based fanout structure bounded by configurable crossbar degrees:

```scala
def fanout_recursive(
  grp: Iterable[RoccNode],
  xbarDeg: Int  // Maximum crossbar fanout
)(implicit p: Parameters): RoccNode
```

Commands are routed hierarchically, with inter-die connections only where necessary. This happens automatically based on your system configuration and the target platform's die topology.

## Summary

| Mechanism | Latency | Use Case |
|-----------|---------|----------|
| Inter-core commands | 2-3 cycles | Work distribution, synchronization |
| Shared scratchpads | 2+ cycles | Data exchange without external memory |
| External memory | 10+ cycles | Large data transfers |

Cross-core communication enables hierarchical accelerator designs without host involvement. Start with the dispatcher-worker pattern, then add shared scratchpads if your cores need to exchange data directly.

## Related Documentation

- [Hardware Stack Overview](/docs/hardware/overview) - Memory channels and core structure
- [Software Stack](/docs/software/overview) - Host-side command interfaces

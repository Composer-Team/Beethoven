---
id: configuration
title: Configuration & Build
sidebar_label: Configuration & Build
---

# Configuration & Build

An accelerator or a piece of an accelerator is described using an `AcceleratorConfig`. An `AcceleratorConfig`
is defined as one of a list of `AcceleratorSystemConfig`. `AcceleratorConfigs` can be concatenated with the
`++` operator to conjoin accelerator descriptions.

```scala
case class AcceleratorSystemConfig(
    nCores: Int,
    name: String,
    moduleConstructor: ModuleConstructor,
    memoryChannelConfig: List[MemChannelConfig] = List(),
    canReceiveSoftwareCommands: Boolean = true,
    canIssueCoreCommandsTo: Seq[String] = Seq.empty,
    canSendDataTo: Seq[String] = Seq.empty
)
```

A "System" is a group of identical cores, which are identifiable by a unique name. This is the name that will
form the namespace in the generated C++ linkage. The user may specify an arbitrary number of cores.

:::tip
Beethoven is built on top of [RocketChip](https://github.com/chipsalliance/rocket-chip) for use of its protocol
[Diplomacy](https://github.com/chipsalliance/rocket-chip/blob/master/docs/src/diplomacy/adder_tutorial.md) framework.
Because of this, you may see a `Parameters` object floating around in various interfaces. `Parameters` is a
map object that allows us to look up various details about the current build without needing to pass around hundreds of
of arguments. `implicit` is a Scala keyword that inspects the caller's scope for an implicit parameter of a given name and
automatically passes in the parameter if it finds one.
:::

## Module Constructor

`moduleConstructor` exposes the constructor of your accelerator core to the build system. There are multiple
options. There are two ways to do this. First, if you are developing your top-level module in Chisel, then you will use
`ModuleBuilder` which takes in a function that maps a `Parameters` object to an Accelerator Core. This is the most common
use-case. If you want nothing to do with Chisel, then you can also use `BlackboxBuilderCustom` to generate a Verilog shell
with a custom command/response interface.

```scala
case class BlackboxBuilderCustom(coreCommand: AccelCommand, coreResponse: AccelResponse) extends ModuleConstructor
```

## Memory and Communication Topology

`memoryChannelConfig` is where you provide a list of memory interfaces (e.g., Readers, Writers) for a core in this sytem.
If you intend for an accelerator core to only be internally visible (other cores can communicate with it but not the host,
then you can specify this using `canReceiveSoftwareCommands`. In such circumstances, we also need to define the communication
topology for these intercommunicating cores. You specify the ways in which cores may communicate with other systems using
`canIssueCoreCommandsTo` and `canSendDataTo` and providing the names of the systems.

See [Cross-Core Communication](/docs/hardware/cross-core) for more details on multi-core topologies.

## Building Your Accelerator

Now that you've constructed an accelerator configuration, you can use a `BeethovenBuild` object to construct your accelerator
for a given platform like so.

```scala
object MyAcceleratorBuild extends BeethovenBuild(new MyAcceleratorConfig,
    buildMode = <BuildMode>,
    platform = <Your Platform>)
// you will see 'MyAcceleratorBuild' as an option when you run `sbt run` in the top directory.
```

First, you must specify which platform you are building your hardware for. We have currently two well-supported FPGA platforms,
the [Kria KV260](https://www.amd.com/en/products/system-on-modules/kria/k26/kv260-vision-starter-kit.html), and the AWS F1/F2
cloud FPGA instances.

Beethoven has two build modes: `BuildMode.Synthesis` and `BuildMode.Simulation`. When building for synthesis, we generate the
hardware and run a platform-specific build flow.

See the [Platform documentation](/docs/platforms/kria) for platform-specific build instructions.

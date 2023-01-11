# Accelerator Configuration

[Up to Hardware](c_hardware.md)

Composer is built on top of the Rocketchip framework (part of Chipyard).
Rocketchip extensively uses a system called _Diplomacy_ to increase the flexibility of Chisel parameterization.
In this section we provide an optional introduction to Rocketchip Diplomacy which may be useful in user designs and
afterwards show to use Diplomacy primitives to configure and generate a Composer system.
Understanding Diplomacy **is not** necessary to using Composer though it may be useful to more complex designs.

## Diplomacy

Chisel allows for modules to be highly parameterized.
For instance, a module can be parameterized with a certain address bit width.
While this is nice for individual modules, a large-scale system may have many hundreds of parameters which is difficult
to coherently supply as a module constructor.
```scala
val my_module = Module(new MyModule(/* hundreds of parameters */))
```

### Configurations
Rocketchip uses *configurations* to parameterize systems.
Configurations are a list of parameters that is provided to a top-level module that uses these parameters to elaborate a
system. For instance, Rocketchip is a repository for elaborating an in-order RISC-V mulit-core system.
At the top-level is the system, which looks at the parameters to figure out what kind of cores to elaborate and how to
individually parameterize them.

As lists, configurations are appendable. In the following code snippet from the Rocketchip repo, a dual core config
consists of parameters that indicate the use of 2 "Big Cores" using a coherent system bus. 
```scala
class DualCoreConfig extends Config(new WithNBigCores(2) ++ new WithCoherentBusTopology ++ new BaseConfig)
```

Let's take a closer look at what `WithNBigCores(2)` does.
```scala
class WithNBigCores(
  n: Int,
  overrideIdOffset: Option[Int] = None,
  crossing: RocketCrossingParams = RocketCrossingParams()
) extends Config((site, here, up) => {
  case TilesLocated(InSubsystem) => {
    val prev = up(TilesLocated(InSubsystem), site)
    val idOffset = overrideIdOffset.getOrElse(prev.size)
    val big = RocketTileParams(
      core   = RocketCoreParams(mulDiv = Some(MulDivParams(
        mulUnroll = 8,
        mulEarlyOut = true,
        divEarlyOut = true))),
      dcache = Some(DCacheParams(
        rowBits = site(SystemBusKey).beatBits,
        nMSHRs = 0,
        blockBytes = site(CacheBlockBytes))),
      icache = Some(ICacheParams(
        rowBits = site(SystemBusKey).beatBits,
        blockBytes = site(CacheBlockBytes))))
    List.tabulate(n)(i => RocketTileAttachParams(
      big.copy(hartId = i + idOffset),
      crossing
    )) ++ prev
  }
})
```
Shown above, `WithNBigCores` is itself a configuration type with a number of parameters, namely how many cores.
When calling the `Config` superclass constructor, `WithNBigCores` provides a lambda that produces a `Map`.
Each key-value pair in the map is called a `Field` within the configuration system.
For instance, shown below is `SystemBusKey` which is a mapping within the config that, if defined, returns a 
`SystemBusParams` type.
```scala
case object SystemBusKey extends Field[SystemBusParams]
```

The lambda provided in the `WithNBigCores` configuration modifies an existing part of the system: whenever the
Rocketchip system tries to find `TilesLocated(InSubsystem)` it needs to find ALL of the tiles. `WithNBigCores`
adds `N` new tiles to that system. So we see that the lambda finds the previous definition with
`up(TilesLocated(InSubsystem), site)`, creates new tiles with `val big = ...` and then sets the new value of
`TilesLocated(InSubsystem)` to the concatenation of `List.tabulate(n)(...) ++ prev` on the last line.

So what did all of this buy us? Now, instead of having a defining all of these parameters explicitly to get a coherent
parameterization, we can simply define parameterizable configurations that handle only a single component of the overall
system and we can mix and match these different components to define the whole system.

How do we access these parameters inside of a design? You might have noticed if you looked at some of the internal 
Composer/Rocketchip code the repetitive use of `(implicit p: Parameters)`. This bit is appended to almost every single
module and function in the entire Composer and Rocketchip code bases.
Given a field such as the prior mentioned `SystemBusKey`, we can extract the value of this field with `p(SystemBusKey)`.

### LazyModules and Interconnect Diplomacy

Whereas normal Chisel uses `Modules` as the (nearly) exclusive type for hardware blocks, Rocketchip uses `LazyModule`
and `LazyModuleImp`.
At a high level, you can think of `LazyModule` as the important blocks within a block-diagram for the system that each
an expected behavior but may have arbitrary implementations, given by `LazyModuleImp`.

These two distinctions allow for a two-phase compilation process where in the first phase, `LazyModules` are
instantiated and allows to negotiate with each other to describe various implementation level details be.
After this phase has completed, the `LazyModuleImp` parts of the modules are elaborated using this information.
Within Composer, this behavior is utilized solely for the purpose of maintaining the memory infrastructure.
For a more concrete look at why this is useful, let's consider the case of a `LazyModule` that has a TileLink protocol
master port that wishes to communicate with memory through a AXI4 slave port. 

```scala

class my_submodule()(implicit p: Parameters) extends LazyModule {
  val mem_node = TLClientNode(/* parameters describing TileLink port*/)
  val module = new LazyModuleImp(this) {
    // can reference `mem_node` to issue memory transactions within this context
  }
}
class my_top()(implicit p: Parameters) extends LazyModule {
  val axi_port = AXI4SlaveNode(/* parameters describing AXI4 port */)
  val sub_mod = LazyModule(new my_submodule)
  // axi_port := sub_mod.mem_node;  DOESN'T WORK! Conflicting protocols
  axi_port := TL2AXI4() := sub_mod.mem_node // this works!
  
  val module = new LazyModuleImp(this) {
    // can implement top-level functionality here
  }
}
```

The first unfamiliar thing about the above example is tha `my_submodule` declares a port.
`LazyModule` instances may declare ports with various parameterizations that their implementations may interact with.
However, interconnect specification is done _entirely_ on the level of LazyModules. 
Within `my_top`, a TileLink master cannot be connected to an AXI4 slave, so we need to use a TileLink-to-AXI4 converter
module. `TL2AXI4` declares a new `LazyModule` within our context and has a TileLink input and an AXI4 output where, once
its inputs and outputs are connected during the diplomacy phase, its implementation can properly convert the TileLink
transactions into AXI4 transactions. Changes within the parameterization of the `TLClientNode` and `AXI4SlaveNode`
change the underlying implementation of the `TL2AXI4` module without any modification to the `TL2AXI4` module (though as
you can see, it requires no parameterization at all).

## Composer Configuration

Composer doesn't generate in-order RISC-V cores, but we still utilize the configuration and diplomacy frameworks to
manage the memory subsystem and multi-"core" structure. Let's start with a simple example of how to create a Composer
configuration without the complicating details of memory infrastructure. 
We will make a Composer system that allows the user to access some simple ALU cores capable of addition, subtraction,
and multiplication.

First we have to make our design. All top-level composer cores must `extends ComposerCore` as detailed in the
[Composer Core Section](c_core.md).
`ComposerCore` is actually a subclass of `LazyModuleImp` and so we need to pass `composerCoreParams` to ensure that it
has enough information to properly configure the memory subsystem, if necessary.
The below snippet shows the basic functionality of the module but notice specifically that the developer **must** tie
off the request and response interfaces that aren't defined in this scope, but rather in the `ComposerCore` superclass.
```scala
// in Examples.scala from Composer-Hardware repo. Code abridged for brevity here
class SimpleALU(composerCoreParams: ComposerConstructor)(implicit p: Parameters) extends ComposerCore(composerCoreParams) {
  val s_idle :: s_working :: s_finish :: Nil = Enum(3)
  val state = RegInit(s_idle)

  val op = RegInit(0.U(io.req.bits.inst.funct.getWidth.W))
  val a = RegInit(0.U(io.req.bits.payload1.getWidth.W))
  val b = RegInit(0.U(io.req.bits.payload2.getWidth.W))
  val result = RegInit(0.U(io.resp.bits.data.getWidth.W))

  io.req.ready := false.B
  io.resp.valid := false.B
  io.resp.bits.data := 0.U
  io.resp.bits.rd := 0.U
  io.busy := true.B

  when(state === s_idle) {
    io.busy := false.B
    io.req.ready := true.B
    when(io.req.fire) {
      state := s_working
      /* Set up state */
    }
  }.elsewhen(state === s_working) {
    /* perform operation */
    state := s_finish
  }.elsewhen(state === s_finish) {
    io.resp.bits.data := result
    io.resp.valid := true.B
    when(io.resp.fire) {
      state := s_idle
    }
  }
}
```

Now that we have a core, we can define a configuration that adds a core of this type to a Composer system.
The below code snippet shows us how - it looks _really_ similar to the `WithNBigCores` configuration from earlier!
Here, we add a number of ALUs to a list specified by the `ComposerSystemsKey` field.
A group of cores is called a "system" and is described by the `ComposerSystemParams` type.
`ComposerSystemParams` has several parameters.
First `coreParams` gives any core parameters.
As of right now, these are limited to per-core memory infrastructure parameters (covered later).
Next, we provide the number of cores and a name for the system.
It is actually important to provide a good `name` because you will reference `name` directly in your software.
Lastly, we tell Composer how to build a core given `coreParams` and `parameters`.
From config to config, this part will likely look much the same.

```scala
class WithALUs(withNCores: Int) extends Config((site, _, up) => {
  case ComposerSystemsKey => up(ComposerSystemsKey, site) ++ Seq(ComposerSystemParams(
    coreParams = ComposerCoreParams(),
    nCores = withNCores,
    name = "ALUSystem",
    buildCore = {
      case (coreParams: ComposerConstructor, parameters: Parameters) =>
        new SimpleALU(coreParams)(parameters)
    }))
})
```

### Composer Configuration with Memory

Now for a slightly more complicated example we will use the `VectorAdder` module from `Examples.scala`.
In this module, we load an array from memory, add 15 to each element, and write the array back to memory.
From this description alone, we know that we will need at least 1 channel to memory for reading and another channel
for writing back.
The following code snippet shows how we add the necessary ports to our module for this functionality.

```scala
// from Examples.scala
class WithVectorAdder(withNCores: Int, dataWidth: Int) extends Config((site, _, up) => {
  case ComposerSystemsKey => up(ComposerSystemsKey, site) ++ Seq(ComposerSystemParams(
    coreParams = ComposerCoreParams(
      memoryChannelParams = List(
        CChannelParams("ReadChannel", 1, CChannelType.ReadChannel),
        CChannelParams("WriteChannel", 1, CChannelType.WriteChannel))
    ),
    nCores = withNCores,
    name = "VectorSystem",
    buildCore = {
      case (composerCoreParams: ComposerConstructor, parameters: Parameters) =>
        new VectorAdder(composerCoreParams)(parameters)
    }
  ))

  // use 8-bit data divisions
  case VectorAdderKey => VectorConfig(dWidth = dataWidth)
})
```

In this example, we use `ComposerCoreParams` and define a few channels:
1. A group of read channels called "ReadChannel" with 1 channel inside
2. A group of write channels called "WriteChannel" with 1 channel inside

How do we use/access these ports from our module? You may remember from the [reader](c_readers.md) and [writer](c_writers.md)
sections.
In the below code snippet, we retrieve this channel group using `getReaderModule("ReadChannel", ...)`.
Having multiple channels in the same group may be useful for instrumenting parallel accesses to different segments of
memory for the same purpose. 

```scala
// inside VectorAdder class in Examples.scala
// parameterization of this module is described in reader section
  val myReader = getReaderModules("ReadChannel", useSoftwareAddressing = true, vConfig.dWidth/8 , vDivs)._2(0) //= 0, vConfig.dWidth / 8, vDivs, Some(0))
```

Another thing of note in the `VectorAdder` example is that you can define your own fields and use them to parameterize
your modules! In this example the width of each element(in bits) is defined by the `dWidth` parameter.

## Memory Parameters

Here lies detailed descriptions of memory channel parameterizations.
Note: As of current implementation, all memory accesses do not obey any sort of coherency protocol.

### Read/Write Channel Group

```scala
class CChannelParams(val name: String,
                     val nChannels: Int,
                     val channelType: CChannelType.CChannelType,
                     val location: String = "Mem")
```

- `name` - Channel group name that allows retrieval within module by `getReaderModule(name)`
- `nChannels` - Number of channels within the group
- `channelType` - Direction of channel. Currently support `CChannelType.ReadChannel` and `CChannelType.WriteChannel`
- `location` - destination of access. Currently only support "Mem"

### Cached Read Channel Group

This produces a group of memory channels that share a cache in between the group and memory.
Lines that have been previously fetched will be available with a 2-3cy latency.
Caution: large caches may fail to pass timing.

```scala
class CCachedReadChannelParams(name: String, nChannels: Int,
                               val cacheParams: CCacheParams,
                               location: String = "Mem")

case class CCacheParams(sizeBytes: Int,
                        idxMask: Option[Long] = None,
                        associativity: Int = 1)
```

- `name` - Channel group name
- `nChannels` - number of channels in the group
- `cacheParams` - description of cache
  - `sizeBytes` - total size of the cache in bytes
  - `idxMask` - bit mask providing which bits to use for the index bits. This can be useful for speciailizing the cache to minimize miss rate if the access pattern is known
  - `associativity` - cache associativity
- `location` - destination of access. Currently only support "Mem"

### Scratchpad

This produces a scratchpad memory that can be retrieved using `getScratchpad(name)`.

```scala
class CScratchpadChannelParams(name: String,
                               val supportMemRead: Boolean,
                               val supportWrite: Boolean,
                               val dataWidthBits: Int,
                               val nDatas: Int,
                               val latency: Int = 2,
                               val specialization: CScratchpadSpecialization = CScratchpadSpecialization.flatPacked)

/**
 * The RocketChip interfaces we use deal in bytes, which may not fit well with the bit-granularity that you may
 * want from your scratchpad memory. Subword loader takes a subword length (in bits), which must evenly divide
 * the cache block size (64B usually) and unpack as many bit-granularity outputs as possible from the payload.
 * Ex. 1B subword, 3b outputs, let A, B, C, ... be outputs that will be written to the scratchpad and 'O' be bits that
 * are ignored.
 * AAABBBOO CCCDDDOO EEEFFFOO ... until the end of the cache line
 * 0        1        2
 *
 * Ex. 2B subword, 3b outputs
 * AAABBBCC CDDDEEEO FFFGGGHH HIIIJJJO ... until the end of the cache line
 * 0        1        2        3
 *
 * A larger subword is more efficient but may be harder to pack together in software.
 *
 * @param wordSizeBits   width of the software word that the datOutWidth fits into
 * @param datsPerSubword how many dats of width 'dataWidthBits' are there per word
 *
 */
case class PackedSubwordScratchpadParams(wordSizeBits: Int, datsPerSubword: Int) extends CScratchpadSpecialization

/**
 * Special case of PackedSubwordScratchpadParams for which there is no padding
 * Ex. 16b data type, 16b software word
 */
class FlatPackScratchpadParams extends CScratchpadSpecialization

```

- `name` - scratchpad name
- `supportMemRead` - allow the scratchpad to be initialized with contents from memory. Member `req` must then be defined with the following fields
  - `memAddr` - beginning of access in memory
  - `scAddr` - beginning index of scratchpad associated with memory region
  - `len` - length of memory access in bytes
- `supportWrite` - allow the scratchpad to be written to by user. `writeReq` field within `access` IO must be defined. Read/Write on same cycle follow behavior defined by Chisel's `SyncReadMem`
- `dataWidthBits` - width of a scratchpad access in bits
- `nDatas` - number of elements in scratchpad
- `latency` - latency of scratchpad access. Supports 1 or 2.
  - Latency 1 uses SyncReadMem without register - may not always pass timing
  - Latency 2 uses SyncReadMem with register - use when timing may be an issue
- `specialization` - due to the specialized nature of custom logic, data may be packed in memory very tightly. Currently support `PackedSubwordScratchpadParams` and `FlatPackScratchpadParams` detailed above.

[Go to next (Software Development)](c_software.md)
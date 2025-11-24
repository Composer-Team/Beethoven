# Platform Integration

In order to add a new platform to Beethoven, you must essentially implement a shim between the Beethoven layer
and the device. The full `Platform` interface is defined [here](https://github.com/Composer-Team/Composer-Hardware/blob/master/src/main/scala/beethoven/Platforms/Platform.scala)
and is intended to provide a comprehensive backbone for Beethoven to generate interconnects and floorplans.
We will go through the entire interface below.

## Front Bus

The front bus is intended to receive commands from the host over some sort of [memory-mapped IO](https://en.wikipedia.org/wiki/Memory-mapped_I/O_and_port-mapped_I/O) (MMIO)
and service responses requests. Because of the breadth of ways this communication may be exposed, we leave it quite open ended and define a `FrontBusProtocol` as an interface
that
1. Defines Diplomacy nodes for delivering RoCC commands
2. Defines top-level IOs

Accordingly, `FrontBusProtocol` is define as:

```java
abstract class FrontBusProtocol {
    def deriveTLSources(implicit p:Parameters) : Config
    def deriveTopIOs(tlChainObj: Any, withClock: Clock, withActiveHighReset: Reset)(implicit p: Parameters): Unit
}
```

### Diplomacy Node Exposure

As an example of how we implement a protocol using this interface, we look to our `AXIFrontBusProtocol` [implementation](https://github.com/Composer-Team/Composer-Hardware/blob/master/src/main/scala/beethoven/Protocol/FrontBus/AXIFrontBusProtocol.scala).

```java
class AXIFrontBusProtocol(withDMA: Boolean) extends FrontBusProtocol {
    ...
    override def deriveTLSources(implicit p: Parameters): Config = {
        // which floorplanning object (e.g., die) contains the front bus interfaces
        // this allows us to place any hardware attached to these interfaces close to the interfaces
        val frontInterfaceID = platform.physicalInterfaces.find(_.isInstanceOf[PhysicalHostInterface]).get.locationDeviceID

        
        // We're going to expose an AXI4 interface to the device so we need to declare it here
        DeviceContext.withDevice(frontInterfaceID) {
        val axi_master = AXI4MasterNode(Seq(AXI4MasterPortParameters(
            masters = Seq(AXI4MasterParameters(
            name = "S00_AXI",
            aligned = true,
            maxFlight = Some(1),
            id = IdRange(0, 1 << 16)
            )),
        )))
        // instantiate the front-hub module which converts AXI4 MMIOs into RoCC commands
        val fronthub =
            DeviceContext.withDevice(frontInterfaceID) {
                val fronthub = LazyModuleWithFloorplan(new FrontBusHub(), "zzfront6_axifronthub")
                fronthub.axi_in := axi_master
                fronthub
            }

        // if there is a DMA port from the host, we can instnatate that
        val (dma_node, dma_front) = if (withDMA) {
            val node = AXI4MasterNode(Seq(AXI4MasterPortParameters(
                masters = Seq(AXI4MasterParameters(
                name = "S01_AXI",
                maxFlight = Some(1),
                aligned = true,
                id = IdRange(0, 1 << 6)
                ))
            )))
            // convert it to TileLink
            val dma2tl = TLIdentityNode()
            DeviceContext.withDevice(frontInterfaceID) {
                dma2tl :=
                    make_tl_buffer() :=
                    LazyModuleWithFloorplan(new LongAXI4ToTL(64)).node :=
                    AXI4UserYanker(capMaxFlight = Some(1)) :=
                    AXI4IdIndexer(1) :=
                    AXI4Buffer() := node
            }
            (Some(node), Some(dma2tl))
        } else (None, None)

        // finally, expose the RoCC interface to Beethoven
        val rocc_xb = DeviceContext.withDevice(frontInterfaceID) { RoccFanout("zzfront_7roccout") }
        rocc_xb := fronthub.rocc_out

        // We return the following 3 keys to Beethoven
        // OptionalPassKey lets us pass arbitrary objects to ourselves when we expose the Top-level IOs 
        //      Since we declared the AXI diplomacy nodes for the host and dma, we'll need to connect them
        //      to the IOs when we construct them
        new Config((_, _, _) => {
            case OptionalPassKey => (axi_master, dma_node)
            case RoccNodeKey => rocc_xb
            case DMANodeKey => dma_front
            // debug only
            case DebugCacheProtSignalKey => fronthub.module.io.cache_prot
        })
    }
}
```


There's quite a bit going on here but we can break it down into two categories.

#### Host Commands

We declare a diplomacy node that corresponds to the communication channel that we're
going to connect to the host: `axi_master`. Because this front-end is intended to facilitate MMIO between
us and the host, we have to implement that functionality. For this reason, we instantiate a `FrontBusHub`,
which implements this MMIO slave port. From this hub, it produces a RoCC diplomacy node, `rocc_out`. Below
the DMA instantation, you see we connect this node to a RoCC crossbar node to add a buffer between the hub
and Beethoven. Finally, we pass crossbar node to Beethoven by placing it in a Config object under the
`RoccNodeKey` key. 

But how are we going to connect `axi_master` to the top-level IOs? Notice that we haven't actually instantiated
them yet. We will do that next in the second `FrontBusProtocol` function. To pass `axi_master` to our function
that we'll define in the future, we put it inside an object under the `OptionalPassKey` key in our Config.

#### Host DMA

In case the device supports DMA from host, we can add an additional AXI port for servicing these reads and writes
that are functionally different from the MMIOs we receive on our `axi_master` port.
This time, instead of connecting it to a `FrontBusHub`, we'll convert it to the TileLink protocol, which Beethoven
uses internally for elaborating the memory interconnect. From this construction we, like before, obtain two objects:
a diplomacy node that corresponds to our top-level DMA IOs (AXI4) and a diplomacy node that corresponds to the
TileLink node that will issue memory transactions into our memory interconnect.

Like with host commands, we need to pass the diplomacy node coresponding to our top-level IOs to ourselves for later
use so we put that, as well, into the `OptionalPassKey` key. Next, for exposing the TileLink node we pass it to
Beethoven under the `DMANodeKey` key as an optional type. If you are not using DMA, then simply pass `None` to this
field.

### Top-Level IO Exposure

To tie the aformentioned diplomacy nodes to top-level IOs, we implement the `deriveTopIOs` function for `FrontBusProtocol`.
```java
def deriveTopIOs(tlChainObj: Any, withClock: Clock, withActiveHighReset: Reset)(implicit p: Parameters): Unit
```

- `tlChainObj: Any`: This is the object that you created and passed to `OptionalPassKey`. As you can see, this is an
    `Any` type, giving you freedom to pass arbitrary objects/information between these functions.
- `withClock: Clock`, `withActiveHighReset: Reset`: In case you need to instantiate any `Module` types, you would do
    it in this function and use these clocks and resets. Be wary of the active-high reset signal.

Here is how we use this function to connect our diplomacy nodes to the AXI nodes in Beethoven.
```java
override def deriveTopIOs(tlChainObj: Any, withClock: Clock, withActiveHighReset: Reset)(implicit p: Parameters): Unit = {
    val (port_cast, dma_cast) = tlChainObj.asInstanceOf[(AXI4MasterNode, Option[AXI4MasterNode])]
    val ap = port_cast.out(0)._1.params
    // instantiate the top-level IO
    val S00_AXI = IO(Flipped(new AXI4Compat(MasterPortParams(
        base = 0,
        size = 1L << p(PlatformKey).frontBusAddressNBits,
        beatBytes = ap.dataBits / 8,
        idBits = ap.idBits))))
    // connect it to our diplomacy node
    AXI4Compat.connectCompatSlave(S00_AXI, port_cast.out(0)._1)

    if (withDMA) {
        val dma = IO(Flipped(new AXI4Compat(MasterPortParams(
            base = 0,
            size = platform.extMem.master.size,
            beatBytes = dma_cast.get.out(0)._1.r.bits.data.getWidth/8,
            idBits = 6))))
        AXI4Compat.connectCompatSlave(dma, dma_cast.get.out(0)._1)
    }

}
```

We use `AXI4Compat` because it provides better naming compared to more Chisel-friendly module types and, as a result,
maps to a AXI4 port when you instantiate a `BeethovenTop` module in Vivado. We provide the `connectCompatSlave` to
connect these Vivado-friendly ports with Diplomacy-friendly AXI4 ports.

### Platform Parameters

In addition to these functions, the platform should also declare the following values to facilitate C++ code generation.
```java
// these are the default values we use for the AXIFrontBusProtocol
override val frontBusBaseAddress: Long = 0
override val frontBusAddressNBits: Int = 16
override val frontBusAddressMask: Long = 0xFFFF
override val frontBusBeatBytes: Int = 4
```

### Alternative Usage Patterns

While we believe this exposure of AXI4 ports will likely be the typical usage-pattern, we have internally used these
functions to test other integrations.

For instance, we tested and verified [ChipKIT](https://github.com/Composer-Team/CHIPKIT/tree/master) integration in this way.
Instead of AXI4 slave ports for communicating with host, we instantiated an ARM M0 CPU core inside of `deriveTopIOs` and connected
it to external UART IOs using the ChipKIT IPs. Because the M0 only has a single AHB port for communicating with instruction SRAM,
data SRAM, external memory, and Beethoven, we did the following:
1. Implemented an AHB filter for these domains
2. Instantiated the SRAMs inside `deriveTopIOs` and connected these to the AHB filter slave side.
3. Convert the AHB Beethoven slave to AXI4 and connect it to a `FrontBusHub` module.
4. Convert the AHB external memory slave to TileLink and expose to Beethoven as a DMA node.

This integration was one our preliminary efforts towards test-chip integration and, while it was functional, had some issues.
Our current test-chip integration is currently a work in progress and we will work towards making it usable by others in a
future release. Our emphasis here is that with these interfaces, you can implement a reasonably sophisticated integration.

## Memory 

Currently, Beethoven exposes AXI4 interfaces to the external memory. While this will be the common case for FPGAs, it may not be
universal. Beethoven instantiates the AXI4 interfaces according to the following parameters as part of your platform declaration:
```java
// these are the default values for the AWS F2
override val hasDiscreteMemory: Boolean = true
override val physicalMemoryBytes: Long = 0x400000000L
override val memorySpaceAddressBase: Long = 0x0
override val memorySpaceSizeBytes: BigInt = BigInt(1) << 34
override val memoryControllerIDBits: Int = 16
override val memoryControllerBeatBytes: Int = 64
override val memoryNChannels: Int = 1
```
- `hasDiscreteMemory` - this is only used for C++ header generation. It informs the Beethoven runtime whether to use the system
    allocator or to instantiate an allocator for allocating regions in the FPGA's discrete address space.
- `physicalMemoryBytes` - the size of the **physical** memory space. This quantity will be generated into the C++ bindings.
- `memorySpaceAddressBase` - the base address offset for the external memory.
- `memorySpaceSizeBytes` - the size of the full address space. That is, if you are on an embedded FPGA and the physical address
    space is much smaller than the virtual address space, you should provide the size of the **virtual address space**. This
    determines the address width of the memory interconnect.
- `memoryControllerIDBits` - the number of **usable** ID bits on the external memory interface. Specifying `0` here will still
    elaborate the `ID` field but it will always be driven 0. Otherwise, Beethoven is free to generate memory requests in the
    range `[0, 1 << memoryControllerIDBits)`. If the number of bits of the field is greater than the number of supported IDs,
    then set this parameter to support the latter.
- `memoryControllerBeatBytes` - the data width of the external memory bus.
- `memoryNChannels` - If you wish to generate multiple different memory channels, increase this parameter. The memory channels
    are **discrete**, as is required by diplomacy. That is, each memory channel is non-overlapping with the other memory channels.
    The above parameters apply to a **single** channel. So if you have two channels, each with 8GB of capacity, you would
    specify `memorySpaceSizeBytes=BigInt(1) << 33`.

## Floorplanning

Beethoven will attempt to generate device-aware floorplans using the information provided to Beethoven as to the device's topology.
The topology presented to Beethoven can correspond directly to the device topology or, for more sophisticated floorplanning, the
developer could specify a more precise topology on top of a device. For simplicity, we'll first device topologies.

The basic interface is shown below for a single-die device. In such cases, there is really nothing more to do and we let our
backend tool handle placement by itself.

```java
// default settings - corresponds to a single-die device
def placementAffinity: Map[Int, Double] = Map.from(physicalDevices.map { dev => (dev.identifier, 1.0 / physicalDevices.length) })
val physicalDevices: List[DeviceConfig] = List(DeviceConfig(0, ""))
val physicalInterfaces: List[PhysicalInterface] = List(PhysicalHostInterface(0), PhysicalMemoryInterface(0, 0))
val physicalConnectivity: List[(Int, Int)] = List()
```

However, if we are deploying designs on an AWS F2 FPGA for instance, those FPGAs are constructed from three silicon dies
connected with Through-Silicon Vias (TSVs). The delay through the TSVs is high and the number of TSVs are limited so we
attempt to minimize crossovers by pinning cores onto specified dies and elaborating the interconnects to minimize die crossings.

On the AWS F2 instances, we expose three dies using unique integral IDs corresponding to a name that will appear in the floorplanning
files.
```java
override val physicalDevices: List[DeviceConfig] = List(
    DeviceConfig(0, "pblock_CL_bot"),
    DeviceConfig(1, "pblock_CL_mid"),
    DeviceConfig(2, "pblock_CL_top")
)
```

Next, we tell Beethoven which dies contain which physical interfaces. For the AWS F2 instances, the host AXI interface is on
die 0 and the memory interface is on die 1. In the future, when we add the support for the many on-chip HBM interfaces, it
will be added here to die 0.
```java
override val physicalInterfaces: List[PhysicalInterface] = List(
  PhysicalHostInterface(0),
  PhysicalMemoryInterface(1, 0)
)
```

Next, we tell Beethoven the connectivity between the dies. The connectivity need not be a [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph), but it often is.
```java
override val physicalConnectivity: List[(Int, Int)] = List((0, 1), (1, 2))
```
Here, we specify that the connectivity is 0 - 1 - 2.

## Platform Fine-Tuning

Finally, Beethoven allows the platform developer to tweak interconnect generation paramters to be more or less aggressive
based on their needs.

```java
// only really used in ASIC mode
val clockRateMHz: Int = 100

// suggest 64 for AWS 
val prefetchSourceMultiplicity: Int = 16

val defaultReadTXConcurrency: Int = 4
val defaultWriteTXConcurrency: Int = 4
val xbarMaxDegree = 2
val maxMemEndpointsPerSystem = 1
val maxMemEndpointsPerCore = 1
val interCoreMemReductionLatency = 1
val interCoreMemBusWidthBytes = 4

/**
* These default values should typically be fine.
*/
val net_intraDeviceXbarLatencyPerLayer = 1
val net_intraDeviceXbarTopLatency = 1
val net_fpgaSLRBridgeLatency = 2

val memEndpointsPerDevice = 1
```

- `prefetchSourceMultiplicity` - What is the longest single transaction a reader/writer should emit (beats)? On AWS platforms, the DDR controller recommends 64
    to be able to achieve maximum DDR efficiency. However, this value linearly impacts the amount of buffering that is required inside of
    the reader/writer.
- `defaultReadTXConcurrency`/`defaultWriteTXConcurrency` - This parameter determines how many concurrent transactions a reader/writer can have in flight. This
    also linearly impacts the amount of necessary buffering and the complexity of the some of the logic. This can be set manually per-reader/writer in their
    configurations for modules that require especially high throughput on only some interfaces.
- `xbarMaxDegree` - the maximum input/output degree for any crossbar in our interconnect generation
- `maxMemEndpointsPerSystem` / `maxMemEndpointsPerCore` / `memEndpointsPerDevice` - memory nodes are reduced in degree before leaving each system and core. These parameters can be
    tweaked to impact the shape of the interconnect.
- `interCoreMemReductionLatency` / `interCoreMemBusWidthBytes` - these parameters impact inter-core communication latencies.
- Intra-Device crossbar latencies - these parameters determine latencies of interconnects on die boundaries.

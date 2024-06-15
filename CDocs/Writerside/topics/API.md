# Beethoven

The following documentation will be split into three sections.
First, there are the hardware development interfaces.
This section includes everything you need to write hardware "cores" and deploy them on a real device.
Second, there are the software interfaces - everything you need to interact with your hardware from a C++ program.
And third, there are the interfaces for adding new device/platform support.
This last section is not necessary for typical hardware development and likely overkill if all you want to do is
develop accelerators for existing platforms.
We encourage readers to be familiar with [Chisel](https://www.chisel-lang.org) before going further as we make extensive
use of their syntax in this documentation.

## Installation

The following script is the general setup for a development platform.
If you are running on an embedded FPGA machine

```Bash
git clone https://github.com/Composer-Team/Composer
# the rest of this script is a copy of Composer/install/setup.sh
cd Composer
git clone --recursive https://github.com/Composer-Team/Composer-Runtime
git clone https://github.com/Composer_Team/Composer-Software
shellr=$(basename $SHELL)
echo "export COMPOSER_ROOT=$(pwd)" >> ~/.$(shellr)rc}

# install software

# 
```

#### Kria Modifications

When running on embedded FPGA platforms, perform the following installation.

```Bash

```


# Hardware Interfaces

## Cores

The only user object that Beethoven considers is accelerator cores.
Groups of cores that perform the same function are called a "system."
A collection of systems comprises an accelerator.

You declare a core in the following way.

```Scala
import chipsalliance.rocketchip.config.Parameters
import beethoven.Systems._

class MyCore(outer: ComposerSystem)(implicit p: Parameters)
 extends AcceleratorCore(outer) {
...
}
```

There's no need to worry about what `p: Parameters` does, just know that all of this is necessary to generate the
scaffolding around cores and systems.
If you want to parameterize your core further, you can do this by simply adding parameters to the list.

```Scala
import chipsalliance.rocketchip.config.Parameters
import beethoven.Systems._

class MyCore(paramB: String, outer: ComposerSystem, paramA: Int)(implicit p: Parameters)
 extends AcceleratorCore(outer) {
...
}
```

## Communication with Host (IO)

Next there are the interfaces that allow the "core" function to be called.
Each access to a core consists of a _request_ and a _response_.
The request contains an arbitrarily large payload or series of payloads and a response contains up to a 48-bit payload.
A request and response have a 1-to-1 correspondence, and a core can only process a single command at a time.

```Scala
class MyCore(...)(implicit p: Parameters) extends AcceleratorCore(outer) {
  val my_req = BeethovenIO(
    new AccelCommand("funcA") {
      val a = UInt(4.W)
      val b = Address()
    },
    new AccelResponse("resp_t") {
      val c = UInt(16.W)
    }
  )
}
```

From the hardware core perspective, this declares
two [decoupled](https://www.chisel-lang.org/docs/explanations/interfaces-and-connections#the-standard-ready-valid-interface-readyvalidio--decoupled)
hardware interfaces: `req` and `resp` corresponding to the command and the response.
Accordingly, the user is responsible for driving the `ready` signal for the `req` channel, and the `valid` and `bits`
for the `resp` interface.

**Addresses:** The width of device-accessible addresses differ from device to device.
To deal with this, we have an `Address` abstraction that allows users to specify registers and pointer arithmetic
without knowing the actual width of the pointer.
`Address` is internally an unsigned integer, so you can access this member if you wish to do `UInt` operations on it
Within commands, .

**What is "funcA" for?:** Equally important for hardware-to-software communication is software-to-hardware.
Whenever you specify this interface and build your accelerator, Beethoven generates C++ functions, accessible from your
software (discussed later), that communicate directly with this hardware interface.
We implement a smart pointer called `remote_ptr` that, depending on the platform, contains a host address and device
address.

For the code above, the generated C++ function may look something like this (namespace declaration and `core_id` will
become clear later):

```c++
namespace my_beethoven_accel {

  response_handle<resp_t> funcA(int core_id, 
    const uint8_t &a, 
    const beethoven::remote_ptr &b);
    
  struct resp_t {
    int16_t c;
  };
};
```

**Can I have multiple functions in the same core?:**
Yes!
This is why "funcA" and the namespace are important as well, it allows differentiation between different interfaces at
different cores.
Different functions in the same core will exist within the same namespace, but with the corresponding function names.
Again, though, ensure that only one command is in-flight at a time in a core.
In the following example, the namespace will include C++ stubs for `funcA` as well as `funcB`.

```Scala
class MyCore(...)(implicit p: Parameters) extends AcceleratorCore(outer) {
  val my_req = BeethovenIO(
    new AccelCommand("funcA") {
      val a = UInt(4.W)
      val b = Address()
    }
  )
  val my_req_2 = BeethovenIO(
    new AccelCommand("funcB") {
      val a = UInt(8.W)
    }
  )
}
```

**Widths:** Due to some implementation details, there is a limitation on the width of output payloads to 48 bits (can
be placed in a 64-bit software type).
Requests, though, can be made arbitrarily large (although we don't recommend
extreme cases).
For high data-throughput we suggest the DMA capabilities mentioned later.

For more advanced/bare-metal functionalities, see the [Raw Commands](#raw-commands) and
[Communcation with Other Cores](#communication-with-other-cores) sections.

Now you should have everything you need to communicate between your core and your host CPU.

## Accelerator Configuration

Before we continue further on programming abstractions, we should discuss how we go from one core to an entire
accelerator.
One feature of Beethoven that hasn't been discussed at length is the idea of having multiple cores.
Task-level parallelism is a common programming paradigm at work in software parallelization frameworks
(e.g., OpenMP([wiki](https://en.wikipedia.org/wiki/OpenMP), [website](https://www.openmp.org))).
However, adding duplicate cores to an accelerator is easier said than done.
For this reason, we make core duplication a primary feature in accelerator generation.

Besides core implementations, the developer needs to declare a Beethoven accelerator configuration.
The following is a common pattern used to add cores to an accelerator.
It is, admittedly, verbose but it can be improved.

```Scala
class WithMyCore(nCores: Int) extends Config((site, here, up) => {
  case AcceleratorSystems =>
    up(AcceleratorSystems, site) ++ List(AcceleratorSystemConfig(
      name = "my_beethoven_accel",
      nCores = nCores,
      moduleConstructor = ModuleBuilder({ case (outer, p) =>
        new MyCore(outer, p)}
      )
    )
})
```

The above code tells Beethoven the number of cores in a system and how to construct one.
It is in the `ModuleBuilder` lambda that you can provide extra parameters to your core if necessary.
Next, we can use this pattern to build accelerators.

```Scala
class MyAccelerator extends Config(
  new WithMyCore(2) ++ new WithBeethoven(platform=AWSF1Platform()
)
object MyAccelerator extends BeethovenBuild(new MyAccelerator, 
  buildMode=Simulation)
```

The above `MyAccelerator` class describes an accelerator with 2 `MyCore` cores with integration for the AWS F1 platform.
We support a variety of platforms (discussed later), and this can be changed without modification to your core
implementation.
Then, the core is elaborated by running the `MyAccelerator` object.
You can select a `buildMode` of `Synthesis` or `Simulation` (`Synthesis` by default).
Some platforms are tricky for us to directly simulate, so the `Simulation` build mode changes certain things about the
elaborated design that make it easier for us and you to simulate.

## Communication with External Memory

Beethoven provides _virtual_ abstractions for communicating with memory - that is, you do not have to worry about
arbitration to a single resource.
The value of this will become clear throughout this section.

Beethoven provides two primary interfaces for interacting with memory: Readers and Writers.
Both of these interfaces are ideal for long, burst reads to a memory segment.
We don't currently have interfaces for short, sparse reads, but these can be added if there is demand.

You access readers and writers in your core implementation using `getReaderModule` and `getWriterModule`, like so:

```Scala
class MyCore(outer: ComposerSystem)(implicit p: Parameters)
  extends AcceleratorCore(outer) {
  val ReaderModuleChannel(req, data) = getReaderModule("my_reader")
  val writerModuleChannel(req, data) = getWriterModule("my_writer")
  val r = getReaderModule("my_other_reader")
}
```

Two observations:
One, these functions return a `[Reader/Writer]ModuleChannel` object.
This can optionally be unpacked into a request and a data channel or kept as a single object like shown with `r` above.
Two, you might notice that these functions don't specify _anything_ about the interface to memory.
That's because these are part of the configuration left out in the previous section.
You can specify how these interfaces are structured using the `memoryChannelParams` member of the
`AcceleratorSystemConfig` object.

```Scala
class WithMyCore(nCores: Int) extends Config((site, here, up) => {
  case AcceleratorSystems =>
    up(AcceleratorSystems, site) ++ List(AcceleratorSystemConfig(
      name = "my_beethoven_accel",
      nCores = nCores,
      moduleConstructor = ModuleBuilder({ case (outer, p) =>
        new MyCore(outer, p)}
      ),
      memoryChannelParams = List(
        ReadChannelParams(name = "my_reader", dataBytes = 2),
        ReadChannelParams(name = "my_other_reader", dataBytes = 4),
        WriteChannelParams(name = "my_writer", dataBytes = 16)
      )
    )
})
```

Above shows a typical usage of `memoryChannelParams`, each specifying the memory channel and the width of the channel.
The name of the accelerator system corresponds to the namespace identifier shown in the [previous C++-generated code
snippet](#communication-with-host-io).
The full definition and usage of `ReadChannelParams` and `WriteChannelParams` is an advanced topic covered in the
[Advanced Memory Channels](#advanced-memory-channels) section.

Each memory channel has a request and a data channel, each with identical fields.

**Request Fields:** A request channel is a decoupled bundle with `address`, and `length`(in-bytes) fields.
For the following, we use readers as an example, but the logic applies equally to writers.
Whenever the request channel handshake occurs (ready and valid both simultaneously high), the reader will begin reading
the segment from memory.
The request channel will not be ready for another request until the entire segment has been read from memory.
For this reason, it is a common idiom to use the `request.ready` field to determine if the entire read has been
performed.

**Data Fields**: Once the module has an active request, the the data channel can be used.
The data channel is a decoupled `UInt` with the length specified by the configuration.
The reader will prefetch data from the segment and the core implementation can consume data on this channel at any rate
it wishes.
The writer emits writes to the memory system as the data becomes available on the channel.
The amount of buffering and aggressiveness of the reader/writer implementations can be tuned to your satisfaction,
though
we provide sensible default values.
See the [Advanced Memory Channels](#advanced-memory-channels) section for more details.

## On-Chip Memory

One of the issues with developing device-agnostic core implementations is on-chip memory.
While FPGA toolchains are "okay" at inferring on-chip memories from large verilog registers, this behavior is basically
non-existent in custom-silicon (ASIC) toolchains.
For this reason, we provide a device-agnostic interface for declaring on-chip memory cells that is more reliable than
relying the FPGA toolchain, and abstracts away many of the headaches of dealing with memory compilers for ASIC
toolchains.

```Scala
object Memory {
  def apply(latency: Int, // latency of read and write latencies
            dataWidth: Int, // width of the memory's data bus in bits
            nRows: Int, // number of datums in the memory
            nReadPorts: Int, // number of dedicated read ports
            nWritePorts: Int, // number of dedicated write ports
            nReadWritePorts: Int, // number of read-write ports
            withWriteEnable: Boolean = false, // enable for byte-wise write-enable
            debugName: Option[String] = None, // optional name for memory cell
            allowFallbackToRegister: Boolean = true // disable to throw error if memory configuration is impossible
           )(implicit p: Parameters, valName: ValName): MemoryIOBundle =
  ...
}
```

The interface is not entirely simple, but should provide you with most of the features you should need for typical
designs.
Before we move on to the returned `MemoryIOBundle` interface for generated memory, a few notes on these parameters.
The on-chip memories supported by a device are not always the exact memory required (or requested) by the designer.
For instance, some ASIC PDKs may only provide memories with Read-Write ports and not support dedicated read and write
ports.
Beethoven attempts to use the available memory cells to "solve" the request of the user.
For instance, a memory with separate read and write ports can be used to service a user request for a memory with a
read-write port.
This functionality is similar to that of [Hammer](https://hammer-vlsi.readthedocs.io), a ChipYard plugin for ASIC flows.

The `MemoryIOBundle` interface resembles the interfaces of typical SRAM cells.
The interfaces are active-high, even if the underlying cells are active-low.

```Scala
class MemoryIOBundle {
  val addr = Input(Vec(nPorts, UInt(addrBits.W)))

  val data_in = Input(Vec(nPorts, UInt(dataWidth.W)))
  val data_out = Output(Vec(nPorts, UInt(dataWidth.W)))

  val chip_select = Input(Vec(nPorts, Bool()))
  val read_enable = Input(Vec(nPorts, Bool()))
  val write_enable = Input(Vec(nPorts,
    if (perByteWrieEnable) UInt((dataWidth / 8).W)
    else UInt(1.W)))

  val clock = Input(Bool())
  ...
}
```

**nPorts**: Each port in this bundle is a vector with the total number of ports for the memory.
Because the ports may not be equal (i.e., read vs write ports), you need to ask the bundle for which port in the vector
corresponds to what you want with the following functions:

- `getReadPortIdx(i: Int)`
- `getWritePortIdx(i: Int)`
- `getReadWritePortIdx(i: Int)`

You can use these functions to index into the above vectors to access the appropriate fields for a read/write/rw port.
Most of these fields do what you think they would do.
Write enable is a 1-bit field if the per-byte write enable is disabled - this field is necessary to drive high if you
want to
write the entire line.
When per-byte write enable is enabled, there is 1-bit per byte on the data bus.
The clock must be provided manually and there is currently not support for multi-clock memories for things like
clock crossings.

## Platforms

Making a hardware design tuned for a new platform is as easy as changing a single line in the build.

```Scala
class MyAccelerator extends Config(
  new WithMyCore(2) ++ new WithBeethoven(platform=AWSF1Platform()))

class MyAccelerator extends Config(
  new WithMyCore(2) ++ new WithBeethoven(platform=KriaPlatform()))
```

Beethoven supports a number of different devices.

- Xilinx Alveo U200 FPGA via AWS F1 Instances
- Xilinx Zynq Family (particularly Kria KV260)
- [CHIPkit](https://ieeexplore.ieee.org/document/9096507) Test Chip

While this is clearly not an expansive list, it has been largely limited by our own
access to hardware, and we chose these devices specifically to demonstrate the potential breadth of our platform support.
It takes a lot of work to understand a device and a lot of effort has gone into making the integration seamless.

To add new platforms, see the [Adding New Platforms](#adding-new-platforms) section.

# Software Interfaces

The Beethoven software repository is broken up into two sections.
A user-space runtime with complete "ownership" of the hardware device, and separate
software processes that use the Beethoven software library to communicate their commands

<img src="software.png" alt="Multiple software processes communicate with a single device management runtime" width="350"/>

The presence of a runtime ensures a number of things: fairness, isolation, and correctness.
Without going to far into the philosophy of this design, let's talk about the runtime.

# Advanced Functionalities

### Raw Commands

### Communication with Other Cores

### Advanced Memory Channels

```Scala
case class ReadChannelParams(name: String,
                             dataBytes: Int,
                             nChannels: Int = 1,
                             maxInFlightTxs: Option[Int] = None,
                             bufferSizeBytesMin: Option[Int] = None)
                             
case class WriteChannelParams(name: String,
                              dataBytes: Int,
                              nChannels: Int = 1,
                              maxInFlightTxs: Option[Int] = None,
                              bufferSizeBytesMin: Option[Int] = None)
```

You might be asking "Why would I want this to be parameterizable from the configuration? Shouldn't this be part of the
core implementation that I write myself?"

### Scratchpad Memories

### Adding New Platforms

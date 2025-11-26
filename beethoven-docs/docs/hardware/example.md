---
id: example
title: Illustrative Example
sidebar_label: Vector Addition Example
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Illustrative Example: Vector Addition

This walkthrough demonstrates implementing a vector addition accelerator in Beethoven, from concept to build.

## The Task

Let's implement a vector addition kernel in Beethoven:

```cpp title="Reference C++ implementation"
// C++ implementation for Vector addition
void vector_add(int *a, int *b, int *out, int len) {
    for (int i = 0; i < len; ++i)
        out[i] = a[i] + b[i];
}

int main() {
    int array_len = 1024;
    int *a   = (int*)malloc(sizeof(int) * array_len);
    int *b   = (int*)malloc(sizeof(int) * array_len);
    int *out = (int*)malloc(sizeof(int) * array_len);
    // initialize vectors
    vector_add(a, b, out, array_len);
    return 0;
}
```

We can start by implementing a module for performing the addition itself.
Beethoven is designed in Chisel HDL, but if you prefer Verilog, you can
integrate Verilog code into Chisel using its [Blackbox](https://www.chisel-lang.org/docs/explanations/blackboxes) abstraction.

<Tabs>
	<TabItem value="Chisel" label="Chisel" default>
```scala title="Chisel vector addition module"
class VectorAdd extends Module {
  val io = IO(new Bundle {
    val vec_a = Flipped(Decoupled(UInt(32.W)))
    val vec_b = Flipped(Decoupled(UInt(32.W)))
    val vec_out = Decoupled(UInt(32.W))
  })
  // only consume an element when everyone's ready to move
  val can_consume = io.vec_a.valid && io.vec_b.valid && io.vec_out.ready
  io.vec_out.valid := can_consume
  io.vec_a.ready := can_consume
  io.vec_b.ready := can_consume
  io.vec_out.bits := io.vec_a.bits + io.vec_b.bits
}
```
	</TabItem>
	<TabItem value="Verilog" label="Verilog">
```verilog
module VectorAdd (
	input clk,
	input reset,
	input [31:0]  vec_a_bits,
	input 	      vec_a_valid,
	output		  vec_a_ready,
	input [31:0]  vec_b_bits,
	input 		  vec_b_valid,
	output		  vec_b_ready,
	output [31:0] vec_out_bits,
	output 		  vec_out_valid,
	input		  vec_out_ready );
wire can_consume = vec_a_valid && vec_b_valid && vec_out_ready;

assign vec_out_bits = vec_a_bits + vec_b_bits;

assign vec_out_valid = can_consume;
assign vec_a_ready = can_consume;
assign vec_b_ready = can_consume;

endmodule
```
	</TabItem>
</Tabs>

Now that we have the addition implemented, how would we go about using this on real hardware?
The reality: it depends. The hardware you have is likely going to have a number of general purpose
memory interfaces. You'll need to provide addresses and a variety of protocol-specific metadata to
access your input vectors and write your output vector. Some examples of how one would do this
using general purpose protocols can be seen [here](https://github.com/aws/aws-fpga/tree/f2/hdk/cl/examples/cl_mem_perf).

Using these general-purpose protocols typically distracts from your core implementation because
strict compliance with the protocol and managing the _physical_ realities of the protocol (i.e., it
may have a fixed location on hardware) has little to do with your implementation. Let's take a
look at how we can use Beethoven abstractions to simplify our vector addition kernel.

## Boilerplate

First, let's start with the boilerplate. For each Beethoven Core, you have a hardware implementation and
an associated Configuration. Click on the tabs to see how we modify the implementation and configuration
at each step.

<Tabs>
        <TabItem value="Implementation" label="Implementation" default>
```scala title="AcceleratorCore skeleton"
import chisel3._
import chisel3.util._
import beethoven._

class VectorAddCore()(implicit p: Parameters) extends AcceleratorCore {
	// implementation goes here
}
```
	</TabItem>
	<TabItem value="Configuration" label="Configuration">
```scala title="AcceleratorConfig"
class VecAddConfig extends AcceleratorConfig(
	AcceleratorSystemConfig(
		nCores = 1,
		name = "myVectorAdd",
		moduleConstructor = ModuleBuilder(p => new VectorAdd()(p))
	)
)
```
	</TabItem>
</Tabs>

`AcceleratorCore` is the top-level Beethoven abstraction for a user's design. You can modularize
your implementation in whatever fashion you'd like, but the module that you plan to expose to the
top-level memory interfaces needs to be an `AcceleratorCore`.
Each `AcceleratorCore` has an associated `AcceleratorConfig` that describes some high-level
details that allow you to provide some high-level build parameters for your accelerator. One that
you can see here is `nCores`. You can increase the number of independent cores on your accelerator
by simply increasing this parameter.


## Host-Accelerator Communication

Next, we need to get the addresses for each of our vectors. The host CPU will need to send these
over to the accelerator. To expose an accelerator function to the CPU, we expose a `BeethovenIO`
in a similar way to `IO()` in Chisel.

<Tabs>
	<TabItem value="Implementation" label="Implementation" default>
```scala
// inside the AcceleratorCore
val my_io = BeethovenIO(new AccelCommand("vector_add") {
	val vec_a_addr = Address()
	val vec_b_addr = Address()
	val vec_out_addr = Address()
	val vector_length = UInt(32.W)
}, EmptyAccelResponse())
```
	</TabItem>
        <TabItem value="Configuration" label="Configuration">
```scala
class VecAddConfig extends AcceleratorConfig(
        AcceleratorSystemConfig(
                nCores = 1,
                name = "myVectorAdd",
                moduleConstructor = ModuleBuilder(p => new VectorAdd()(p))
        )
)
```
        </TabItem>
	<TabItem value="c" label="Generated C++">
```cpp
namespace myVectorAdd {
        beethoven::response_handle<bool> vector_add(
		uint16_t core_id,
		uint32_t vector_length,
		beethoven::remote_ptr vec_a_addr,
		beethoven::remote_ptr vec_b_addr,
		beethoven::remote_ptr vec_out_addr);
};
```
	</TabItem>
</Tabs>

The above snippet does several things.
First, the command and response are both provided with names.
The name `vector_add`, allows Beethoven to generate a software interface for your code
that will be called `vector_add.`
This function will take in the the arguments as specified and return an acknowledgement.
Responses can also carry payload, but we exclude that functionality for simplicity in this example.
Second, you'll notice `Address()` is not a typical Verilog or Chisel type. We provide
it to abstract away from platform-specific address-widths and provide a uniform interface.

To read more about the full specification of `BeethovenIO`, see [Host Interface](/docs/hardware/host-interface).

## Adding Memory Interfaces

Now that we have a way of obtaining the necessary function arguments from the host, we need to read
our operands from memory. We can do this by declaring a `Reader`. Usually you would have to read up
on the available interfaces for your platform - here, there's no need, just declare them.

<Tabs>
	<TabItem value="impl" label="Implementation" default>
```scala
// inside AcceleratorCore
val vec_a_reader = getReaderModule("vec_a")
val vec_b_reader = getReaderModule("vec_b")
val vec_out_writer = getWriterModule("vec_out")
```
	</TabItem>
	<TabItem value="config" label="Configuration">
```scala
class VecAddConfig extends AcceleratorConfig(
        AcceleratorSystemConfig(
                nCores = 1,
                name = "myVectorAdd",
                moduleConstructor = ModuleBuilder(p => new VectorAddCore()(p)),
		memoryChannelConfig = List(
			ReadChannelConfig("vec_a", dataBytes = 4),
			ReadChannelConfig("vec_b", dataBytes = 4),
			WriteChannelConfig("vec_out", dataBytes = 4)
		)
        )
)
```
	</TabItem>
</Tabs>

For each reader/writer, the physical data bus width is specified in the configuration.
These can be made arbitrarily large or small with some restrictions. Read more in the [Memory Interfaces](/docs/hardware/memory) documentation.

## Full Implementation

Finally, we have all of the primitives we need to connect our vector addition module and
use it on real hardware.
Below, you can see the full implementation.

:::note Initialize Outputs
Always initialize all outputs to prevent latches. Use `false.B` for Bools, `DontCare` for unused signals.
:::

<Tabs>
        <TabItem value="impl" label="Implementation" default>
```scala title="Complete vector addition core"
import chisel3._
import chisel3.util._
import beethoven._
import beethoven.common._
import chipsalliance.rocketchip.config.Parameters

class VectorAddCore()(implicit p: Parameters) extends AcceleratorCore {
  val my_io = BeethovenIO(new AccelCommand("vector_add") {
    val vec_a_addr = Address()
    val vec_b_addr = Address()
    val vec_out_addr = Address()
    val vector_length = UInt(32.W)
  }, EmptyAccelResponse())

  val vec_a_reader = getReaderModule("vec_a")
  val vec_b_reader = getReaderModule("vec_b")
  val vec_out_writer = getWriterModule("vec_out")

  val vec_length_bytes = my_io.req.bits.vector_length * 4.U

  // from our previously defined module
  val dut = Module(new VectorAdd())

  /**
   * provide sane default values
   */
  my_io.req.ready := false.B
  my_io.resp.valid := false.B
  // .fire is a Chisel-ism for "ready && valid"
  vec_a_reader.requestChannel.valid := my_io.req.fire
  vec_a_reader.requestChannel.bits.addr := my_io.req.bits.vec_a_addr
  vec_a_reader.requestChannel.bits.len := vec_length_bytes

  vec_b_reader.requestChannel.valid := my_io.req.fire
  vec_b_reader.requestChannel.bits.addr := my_io.req.bits.vec_b_addr
  vec_b_reader.requestChannel.bits.len := vec_length_bytes

  vec_out_writer.requestChannel.valid := my_io.req.fire
  vec_out_writer.requestChannel.bits.addr := my_io.req.bits.vec_out_addr
  vec_out_writer.requestChannel.bits.len := vec_length_bytes

  vec_a_reader.dataChannel.data.ready := false.B
  vec_b_reader.dataChannel.data.ready := false.B
  vec_out_writer.dataChannel.data.valid := false.B
  vec_out_writer.dataChannel.data.bits := DontCare

  dut.io.vec_a <> vec_a_reader.dataChannel.data
  dut.io.vec_b <> vec_b_reader.dataChannel.data
  dut.io.vec_out <> vec_out_writer.dataChannel.data

  // state machine
  val s_idle :: s_working :: s_finish :: Nil =  Enum(3)
  val state = RegInit(s_idle)

  when (state === s_idle) {
    my_io.req.ready := vec_a_reader.requestChannel.ready &&
      vec_b_reader.requestChannel.ready &&
      vec_out_writer.requestChannel.ready
    when (my_io.req.fire) {
      state := s_working
    }
  }.elsewhen(state === s_working) {
    // when the writer has finished writing the final datum,
    // isFlushed will be driven high
    when (vec_out_writer.dataChannel.isFlushed) {
      state := s_finish
    }
  }.otherwise {
    my_io.resp.valid := true.B
    when (my_io.resp.fire) {
      state := s_idle
    }
  }
}
```

:::tip State Machine Pattern
The state machine waits for all three channels to be ready simultaneously before accepting commands, preventing partial transaction deadlock.
:::

        </TabItem>
        <TabItem value="config" label="Configuration">
```scala
class VecAddConfig extends AcceleratorConfig(
        AcceleratorSystemConfig(
                nCores = 1,
                name = "myVectorAdd",
                moduleConstructor = ModuleBuilder(p => new VectorAddCore()(p)),
                memoryChannelConfig = List(
                        ReadChannelConfig("vec_a", dataBytes = 4),
                        ReadChannelConfig("vec_b", dataBytes = 4),
                        WriteChannelConfig("vec_out", dataBytes = 4)
                )
        )
)
```
        </TabItem>
</Tabs>

## Building For A Target Platform

Now we have a full implementation of an accelerator that we'll be able to use and
deploy on real hardware! The final step is to build it. With the following code and
some basic environment setup, we can build, simulate, and synthesize our accelerator
for FPGA. All that is necessary is the `BuildMode` and the target platform, Beethoven
handles the rest.

```scala
object VectorAddConfig extends BeethovenBuild(new VectorAddConfig,
  buildMode = BuildMode.Synthesis,
  platform = new AWSF2Platform)
```

In this example we've shown an example of how we would deploy an accelerator with a
vector addition core. However, we can build far more complex accelerators, with different
core implementations of the same accelerator and with many more cores of each type.

See [Configuration & Build](/docs/hardware/configuration) for more details on build options.

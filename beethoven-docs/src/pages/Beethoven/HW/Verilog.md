
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Verilog Support

Beethoven primarily supports Chisel HDL but allows the use of Verilog in two primary ways.
First, we support exporting the accelerator core as a Verilog shell, and second we leverage
Chisel's [Blackbox](https://www.chisel-lang.org/docs/explanations/blackboxes) abstraction
for linking in external verilog sources. 

### Exporting a Verilog Shell

During configuration of your accelerator design, you specify the constructor for your accelerator.

When you use `BlackboxBuilderCustom`, you provide the accelerator command and response interfaces and
Beethoven constructs a Verilog shell with that interface. For instance:

<Tabs>
<TabItem value="a" label="Configuration" default>
```java
class MyAcceleratorConfig extends AcceleratorConfig(
  AcceleratorSystemConfig(
    nCores = 1,
    name = "MyAcceleratorSystem",
    moduleConstructor = BlackboxBuilderCustom(new AccelCommand("my_accel") {
      val addend = UInt(32.W)
      val vec_addr = UInt(32.W)
      val n_eles = UInt(20.W)
    }, EmptyAccelResponse()),
    memoryChannelConfig = List(
      ReadChannelConfig("vec_in", dataBytes = 4),
      WriteChannelConfig("vec_out", dataBytes = 4))
)
```
</TabItem>
<TabItem value="v" label="Generated Verilog Shell">
```verilog
module MyAcceleratorSystem (
  input clock,
  input reset,

  input         cmd_valid,
  output        cmd_ready,
  input  [19:0] cmd_n_eles,
  input  [31:0] cmd_vec_addr,
  input  [31:0] cmd_addend,
  output        resp_valid,
  input         resp_ready,
  output        vec_in_req_valid,
  input         vec_in_req_ready,
  output [33:0] vec_in_req_len,
  output [63:0] vec_in_req_addr_address,
  input         vec_in_data_valid,
  output        vec_in_data_ready,
  input  [31:0] vec_in_data,
  output        vec_out_req_valid,
  input         vec_out_req_ready,
  output [33:0] vec_out_req_len,
  output [63:0] vec_out_req_addr_address,
  output        vec_out_data_valid,
  input         vec_out_data_ready,
  output [31:0] vec_out_data
);

endmodule
```
</TabItem>
</Tabs>

### Linking In External Sources

To link in external sources, we have added an additional utility for linking external sources and
directories to the Beethoven backend.
```java
BeethovenBuild.addSource(p: Path)
```
The path object is from the very useful [Scala os-lib package](https://github.com/com-lihaoyi/os-lib).
The following is an example of how we use this utility to link in the FPUs that we generate from
the [FPnew](https://github.com/openhwgroup/cvfpu) library.

```java
val blackbox = Module(
new FPNewBB(floattype = floattype,
  floatwidth = floatwidth,
  lanes = lanes,
  operationSupport = FPNewOpSupport(a, d, n, c),
  source = sourceTy))
// blackbox returns a list of paths (e.g., os.Path("/home/chris/my_fpnew/fpnew_top.sv"))
blackbox.sources.foreach(BeethovenBuild.addSource)

//
// clock & reset
blackbox.io.clk_i := clock
blackbox.io.rst_ni := ~reset.asBool

// request
blackbox.io.operands_i := Cat(io.req.bits.operands.map(a => Cat(a.reverse)).reverse)
blackbox.io.rnd_mode_i := io.req.bits.roundingMode.asUInt
blackbox.io.op_i := io.req.bits.op.asUInt
blackbox.io.op_mod_i := io.req.bits.opModifier
blackbox.io.src_fmt_i := io.req.bits.srcFormat.asUInt
blackbox.io.dst_fmt_i := io.req.bits.dstFormat.asUInt
blackbox.io.int_fmt_i := io.req.bits.intFormat.asUInt
blackbox.io.vectorial_op_i := 1.B
blackbox.io.tag_i := 0.B
blackbox.io.in_valid_i := io.req.valid
io.req.ready := blackbox.io.in_ready_o

// response
val resp_split = (0 until lanes) map (i => blackbox.io.result_o((i + 1) * floatwidth - 1, i * floatwidth))
io.resp.bits.result zip resp_split foreach { case (o1, o2) => o1 := o2 }
io.resp.bits.status := blackbox.io.status_o.asTypeOf(io.resp.bits.status)
io.resp.valid := blackbox.io.out_valid_o
blackbox.io.out_ready_i := io.resp.ready

// flush & flush
blackbox.io.flush_i := false.B
blackbox.sources
```

Following the successful build of your hardware, the sources will be copied into your build directory.
To use the links inside your code, you will need to write a [Chisel Blackbox](https://www.chisel-lang.org/docs/explanations/blackboxes) for them.

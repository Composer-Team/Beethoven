# Motivation

For performance critical tasks, it sometimes becomes necessary to consider hardware accelerators.
One of the most common examples is the GPU, which specializes in vector operations.
GPUs have been particularly successful because vector operations comprise much of AI (matrix multiplies) and scientific 
computing (iterative simulations).

However, not everything fits well into the vector operation model, for instance, signal processing, which can be
accelerated by custom circuits.
While manufacturing a custom circuit is well outside of the budget for most people, there is the Field Programmable
Gate Array (FPGA) which can simulate circuits.
However, writing programs that describe circuits for custom silicon and FPGAs is _difficult_.
This is for a couple reasons.

First, the programming abstraction is pedantic.
Whereas high level languages (e.g., C++) can describe complex semantics in a line or two, circuits are described in
Hardware Design Languages (HDLs) which use Register-Transfer Level (RTL) logic.
RTL logic describes a program as a set of state holding elements (registers) and combinational logic between them.
Consider the following code:

```c++
// at the start of execution, set an int called `a` to 4
int main() {
  int a = 4;
}
```

This is some trivial behavior and describes the initialization of state in the program.
Now consider how this would be done as part of a circuit.

```
module MyModule(clock, reset);
input clock;
input reset;

// declare a 32-bit register called 'a'
reg [31:0] a;

// traditionally, state transfers happen at the positive edge 
// transition of the clock signal 
always @(posedge clock)
begin
// traditionally, when reset=0, this tells the circuit to setup
// into initial values
    if (!reset)
    begin
// assign the register a to a 32-bit decimal literal 4
        a <= 32'd4;
    end
end

endmodule
```

This code is written in Verilog and is obviously much more complicated.
Accordingly, this makes hardware design much harder to write in terms of time and debugging.
In recent years, the community has developed HDLs inside more capable languages.
For instance, there is [MyHDL](https://github.com/myhdl/myhdl) for developing hardware inside of Python, and [Chisel](https://www.chisel-lang.org)
for developing hardware inside of Scala.
While our work does support the use of Verilog, we best support Chisel and will use it from here on out.

Chisel offers some improvements to expression in HDLs.
For instance, here is the previous code snippet written in Chisel.
```Scala
class MyModule extends Module {
    val a = RegInit(4.U(32.W))
}
```

You'll notice that the `clock` and `reset` signals are gone.
Since these signals are essentially required for any reasonable hardware development, these are implicitly declared
as part of the `Module` class.
Then, `RegInit` provides an interface for declaring a register with an initial value `4.U(32.W)`, a 32-wide unsigned
integer with value `4`.

Unfortunately, but necessarily, HDLs are verbose.
The efficiency gains in circuits comes in some part due to the customizability of the circuit to the particular needs of
the application.
A 16-bit integer will use half of the chip area as a 32-bit integer.
And when it comes to combinational circuits, these payoffs can be multiplicative.

We won't discuss the details of circuit design or Chisel here, but we believe that current works have made huge steps
forward in improving how circuits are described.
So then what's next? 
Circuits aren't the end of the story.

While a circuit implementation of a function may very well accelerate your application, how do you actually run it?
There are three options.
One, you simulate it in software.
This will never outperform a software implementation and is only worthwhile for debugging your circuit.
Two, you manufacture a chip (\$\$\$).
Or three, you deploy it on an FPGA (\$).

Options two and three are the only realistic ways to gain a performance/energy improvement, but force you to deal with
some serious realities: hardware/software integration and chip layout.
These problems are only tangentially addressed by improvements to HDLs and are, in these authors' opinions, a more
difficult challenge than the actual implementation of the circuit.
In the following sections, we'll discuss these challenges, after which, you'll understand the motivations to Beethoven.

### Hardware/Software Integration

How do you intend for a circuit to interact with your program?
How do I reset the circuit?
How does the circuit read the C++ vector I just wrote to memory?

The answer is always: it depends.
If your accelerator is resembles a GPU and is installed on a PCIE slot, you'll need to write PCIE drivers for your
CPU to communicate over the bus to the chip (both moving data and control operations like reset).
If you're running your circuit on an FPGA installed on the same die as your CPU, then you'll need to read your CPU's
device documentation to see how the manufacturer intended for the CPU and FPGA to interact.

Then, consider the perspective of the circuit.
While the circuit written in the above examples is certainly valid, it doesn't interact with a PCIE bus.
But if you want to use it on a device connected to the host via PCIE, you'll need it to.
And if you want to run it on a device integrated in a different way, you'll need to rewrite everything for whatever
communication protocols were prescribed by the manufacturer.

And now consider memory! 
You've heard that DDR is a common memory protocol and you're feeling bold so you want to implement your own integration
between your circuit and the DDR-based device so you can read things from memory (**do not do this**).
Not only do you have to pay money (quite a bit actually) to even read the protocol specification, but once you read it
you realize it is way above your pay-grade to be thinking about these things so you "just" acquire a license for a
proprietary DDR controller (IP) so you can use a "simpler" protocol instead.
The specifics of this protocol and IP behaves depending on your usage of the protocol also change based on things that
require you to understand what the DDR memory device is doing anyway.
And if you don't consider these things and thoroughly read the IP documentation, you may find yourself running into
performance bugs that cannot be resolved unless you do.

By the end of this process, you understand the internals of your memory device, the proprietary IP you're using to
talk to this device, and a handful of arcane communication protocols, and you'll have written tens of thousands of lines
of code in a handful of software and hardware languages - all of this actually have nothing to do with the application
you were trying to accelerate in the base case.
All to see "Hello World" come out of your circuit.

Beethoven seeks to simplify hardware/software integration so that you can write device-agnostic code and easily re-use
integration written by people that understand the device.
This way, you run your "Hello World" at peak performance without writing ten thousand lines of superfluous code and
across a variety of devices.

### Chip Layout

Turning a program that describes a circuit into an actual circuit implementation is a complex process.
For the rest of this discussion we'll consider custom silicon implementation, but a similar process and set of issues
applies for FPGAs.

In a similar way to how a software compiler lowers high-level semantics into low-level operations
(e.g., x86 instructions), the hardware compilation process lowers circuit programs into low-level physical devices
(e.g., gates, registers).
This step is called "logic synthesis," and involves both mapping operations and optimizing the circuit to meet three
goals: timing closure, area minimization, and power minimization.
The gates that are available for synthesis are provided by the manufacturer in a "Process Development Kit"'s (PDK)
standard cell library.

#### Synthesis

Whenever you compile a circuit with 32-bit registers `a[31:0]`, and `b[31:0]` with combinational path `b := a + 4`,
the synthesizer must first map `a` and `b` to registers (1-bit registers are typical in a PDK), resulting in a total 
of 64 register cells.
Then, the combinational path includes a 32-bit adder requiring approximately a hundred gates.
The PDK may also include gates specifically for performing adds, which can reduce this to approximately 32 gates.

<img src="carry_add.png" alt="Convert table to XML" width="350" border-effect="line" background="@color/white"/>

Now, with the cells mapped, the synthesizer considers timing closure: "Given a desired clock frequency $f$,
for all paths a[i] to b[i], does the signal propagate in time less than $\frac{1}{f}$?"
For instance, consider the path to b[31] (the highest-order bit).
It depends on a[31] as well as the 31 previous intermediate results from the addition, meaning the signal must propagate
through 32 gates in under $\frac{1}{f}$ seconds to successfully meet timing closure.
For a 1GHz clock rate, this is a 1ns timing window.

Synthesizers are great at synthesizing dense combinational logic but ignore one important part: wire delay.
For timing closure, synthesizers look primarily at how long it takes for signal to propagate through the gates, but not
at how long it takes for signal to propagate through the wires connecting these gates.
There are heuristics that synthesizers use to estimate this quantity, but the only real way to know is to perform
"logic placement."

#### Placement and Routing (PnR)

Synthesis generates a gate netlist: a Verilog file containing a list of gates declared in the PDK,
and wires connecting these gates to each other and to the inputs/outputs.
However, the netlist lacks the spatial element of "where" each cell is and how the wires between these cells are drawn.

PnR tools take in the gate netlist, place the cells in a grid, and perform more precise timing analysis, now that there
is spatial information to account for how far cells are away from each other.
PnR tools are phenomenal at optimization of dense modules with local logic.

Why? Because when you look at a gate netlist, the assignment of one thing to another looks the same as any other 
assignment.
Consider the following code:

```Scala
class MyHUGEModule extends Module {
    val io = IO(new Bundle {
        val w, x = Output(...)
        ...
    }
    ...
}
class MyModule extends Module {
    val a, b, c = Reg(...)
    val q, r = Reg(...)
    val otherModule = Module(new MyHUGEModule)
    a := otherModule.io.w
    b := otherModule.io.x
    c := a + b
    q := q + r
}
```

In the above snippet, there is no spatial information: we don't know where the outputs to `otherModule`, `a`, `b`, or `c`
will be.
But, it's usually a safe assumption to make that all of the terms can be placed in such a way that the assignment to
`a` and `b` can be made.
In addition, you might think...
> if a + b passes timing, then surely q + r will too!

<img src="wire_delay.png" alt="Placement of w, x cause timing failure in c" width="500" style="block"/>

In reality, these might not be reasonable assumptions.
Some signals might be very far away from each other necessarily, and result in hard-to-resolve timing errors.
The tool, for instance, might report that the assignments to `a`, `b`, and `q` pass timing while the assignment to `c`
fails.
If your mental model for the placement looks like (a) in the figure above, this may lead you to believe that something 
about the addition of `a + b` is more expensive and that we have to find a more optimized way to do `+`.
In reality, the real placement might look more like (b): the outputs of module `MyHUGEModule` are far away from each
other so that `a` and `b` are far from each other, causing wire delay to induce a failure in `a + b`. 

When operands are close, placement is easy, and PnR tools can more or less automatically place a design.
But what is the problem that Beethoven wants to solve here?
Generally speaking, we believe that functions are dense.
And because function are so dense, when we have multiple functions on the same device, the functions are placed sparsely
relative to each other.
When different functions want to share a resource (e.g., a DDR memory channel), there is a contention between
the sparse placement of dense functions with a real, fixed position of a shared resource.

Like the issues discussed in [Hardware/Software Integration](#hardware-software-integration), these considerations have
very little to do with functionality.
Nevertheless, you have to deal with these issues if you want your design to pass timing closure.
Beethoven provides abstractions for dense modules called "cores" that developers put their kernel logic in,
so that the developer can worry about the functionality of their dense modules while Beethoven handles the placement,
floor-planning, and buffering on-chip connectivity so that these aforementioned placement issues do not arise.











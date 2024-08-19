# VLSI

# Floorplanning and Pre-Implementation Design

You need to think about how your design is going to be structured before you synthesize it - it is essential for good
QoR. Some rules of thumb:

1. While Chisel/SystemVerilog support parameterizable modules, do not over-parameterize - having identically parameterized
   modules **drastically** simplifies synthesis/pnr effort. Use parameterize for big things that will have a sizeable
   impact on QoR. For other things, provide them as an input wire to the module. 
    - Consider the "adder." If you want to subtraction, you could either
      small modifications to the adder module to support subtraction or you could make an entirely separate subtractor
      module. How you trade off quality of results (QoR) for your valuable time is up to you...
    - A real world for-instance is the tiled MCMC accelerator that I made for my first project at Duke. These tiles were
      organized in a grid. The PEs at the edges are a special case so I included awareness of these special cases in
      the module parameterization. In effect, it meant that I had to synthesize and implement 18 different modules. The
      implementation was much, much more complicated and for basically no benefit. The area of each module was
      essentially identical whereas this flow required me to completely automate every step of the process (a lot of work).
      Instead, I should have just added input wires to communicate this "edge" case to the PE.
2. Avoid `Vec` inputs and outputs. You need to be careful about when you use vectors and use them purposefully. If you
   are not going to use a `Mux`, consider using a Scala collection like `Seq` or `List`. The only additional operator
   that `Vec` realistically gives you is access via a `UInt` index.
   -  If you need to use a `Mux`, be aware of their expense - they can be fine at low clock rates but be terrible at
      high clock rates. They scale differently on different devices as well. For instance, Synopsys can do _retiming_
      across muxes whereas Vivado cannot.
3. Avoid global communication except wherever strictly necessary. Two instances of global, synchronization that can
   cause problems in high-performance designs: clock and reset.
   - **CLOCK**: The clock signal is necessarily globally synchronous, but CAD tools are great at dealing with this long signal
     when logic is mostly local. Why? Because the clock in the local case is pretty close to ideal. On the other hand,
     for global signals, there is significant _clock drift_.
   - **RESET**: For reset, you're dealing with a control signal that needs to be basically everywhere on the chip at once.
     For slower clock rates, just leaving it as a control signal is probably fine. For higher clock rates, you're going
     to end up with a lot of placement congestion and poor QoR if you don't do something. What you do in such a case is
     pipeline the reset signal. You should have a rough idea of where you want your modules to be placed and build a
     reset network around this. This will not affect your synthesis QoR, but will significantly affect PnR results.
   - As for other signals, they suffer from the same problems as clock and reset. When if comes to global signals, I did
     some very rough math to figure out the worst-case rate of signal propagation at 65nm and it was something like
     3mm/ns. This could be way off - I forget the exact number but do try to keep signal propagation short. 

TODO: add picture of clock drift

TODO: add picture of reset network

# High-Level Flow

In the RTL -> Synthesis -> Place & Route pipeline, synthesis is the first step and turns behavioral RTL
into a gate netlist. The gate netlist is a verilog file that contains instantiations of library cells and wires that
connect them. Library cells include things like `AND`, `OR`, `DFF` (D-Flip-Flop). The propagation delay of wires is
not considered in synthesis.
We typically use Synopsys Design Compiler (DC) for synthesis but Cadence offers their own synthesis tool called Genus.
I haven't used it, but I know other groups do. Typically, I believe Synopsys is the industry standard synthesis tool but
I could be wrong.

Place and route (PnR) takes a gate netlist and implements it in silicon using a manufacturer's process development kit (PDK).
We typically use Cadence Innovus for PnR, but Synopsys offers their own PnR CAD tools called ICC2. Generally speaking,
ICC2 is considered more automated but Innovus achieves better QoR, so we use Innovus.
PnR has several main outputs.

First, there are `.lef` files. LEF files contain the geometry of a cell. The cell can be a
single gate, or it can be an entire CPU, or anything in between. 

Second, there is `.gds2`. This contains all of the information necessary for taping out a chip and it's what you give to
the fab. You don't need to worry about the contents of this file and the only thing you're likely to be doing with it
(besides giving it to someone else) is using it for post-PnR design checks (aka DRC, or design-rule checking).

Finally, there is `.lib` or "LIBERTY". This is an text-based format that contains timing, power, and IO information
about a cell. If you compile a sub-design and PnR it, you can use the `.lib` file in other synthesis runs as a subcomponent
instead of synthesis needing to actually consider the RTL for the sub-design.
# Synthesis


## Basic Top-Level Script

## Hierarchical Flows & Floorplanning

We previously mentioned the important of design floorplanning, but there's also an element of floorplanning with how
you plan to synthesize and implement your design.

One extreme is taking the RTL for your whole design and doing a synthesis from the top level that includes every
component in your design. This is possible for smaller designs and will (theoretically) achieve the best QoR, but,
without special effort, scale poorly and take months to compile.

Another extreme is that you synthesize each leaf module, do PnR, get the output products that let you use that module as
a cell in the parent module, synthesis, PnR, repeat... PnR can be a very manual process to achieve dense results and
present a challenge: you are permanently deciding the shape of a module before you know what the rest of the design
looks like. As you might guess, the ideal way is somewhere in the middle.

In additional in-between, you can do a bottom-up compile: synthesize a submodule, mark it as `dont_touch`, and then
synthesize the parent module. This provides quicker turnaround, but prevents the synthesizer from considering
cross-boundary optimizations. Whether the design features ample opportunity for cross-boundary optimizations is up to
you. Make sure that you set input


### IO timing

### SRAM

## Optimization

## Outputs

# Implementation / PnR (Cadence Innovus)

# Appendix

## `.lib`, `.db`

Synopsys products use a Synopsys-specific library file format (`.db`). On the other hand, many PDKs
(e.g., ASAP7) only provide `.lib` files for cells  and Cadence products will only output `.lib`.
You can use the Synopsys library compiler (`lc_shell`) to convert between formats.

```
% Convert `.lib` to `.db`
read_lib my_library.lib
% This will read in the library. The "name" of the library may be
% different from the file name and the tool will provide the name of
% the library when it gets read in
write_lib -format db <name_of_library> 
```

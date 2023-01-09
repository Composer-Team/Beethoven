# Memory Subsystems

[Up to Hardware](c_hardware.md)

## Organization
- [Readers](c_readers.md)
- [Writers](c_writers.md)
- [Scratchpad]()

## Overview

Accessing memory in software is very different from accessing memory in hardware designs. First of all, in software
there isn't really a concrete idea of "physical" memory - there's just types and arrays of types (this is of course a
simplification).
Only when you get into bare-metal optimization do programmers every get any sort of exposure to the nitty gritty of
what's happening (e.g. NUMA, memory coherence) but even so, the instrumentation of these actions are abstracted away.

When it comes to hardware design, the abstraction layers are almost vanished and users need to not only worry about
correctly interfacing with memory but weighing the benefits of what _kind_ of memory they want, for instance. For the
limited case of the Amazon AWS FPGAs, there are FFs, BRAM, URAM, and DRAM.
While you may know what the data flow of our algorithm looks like, how you implement that data flow with a set of
structures each with their own unique behaviors is less clear.

Selecting which memory impelementation, understanding its behavior, and correctly and efficiently interacting with it
is challenging. For this reason, many High-Level Synthesis (HLS) tools abstract away from these memory implementations
using high-level interfaces. Of course abstraction nearly always comes at the cost of performance but so long as these
abstractions can efficiently map to the intended behavior of the user, then the overheads may be acceptable.

Composer exposes HLS-like interfaces with memory readers, writers, and then a BRAM/URAM scratchpad.
A simple read-only cache system is available for readers.
Write-capable caches, among other features may be added in future releases.
If you have a general memory structure that would be useful to have within the Composer framework,
please reach out.

[Next (Readers)](c_readers.md)
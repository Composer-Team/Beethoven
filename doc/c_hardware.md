# Core Integration

[Up to index](index.md)


## Organization
- [Composer Core](c_core.md)
- [Memory Subsystem](c_memory.md)
    - [Readers](c_readers.md)
    - [Writers](c_writers.md)
    - [Scratchpad]()
- [Accelerator Configuration]()

## Introduction
Given a user functional design, Composer simplifies deploying it into a multicore system
that is intuitively accessible from a C++ software context. This requires the user
hardware design to interface correctly with hardware constructs, which should result in
easy-to-use interfaces when developing software.

![](resources/composer.png)

At a high level, a user-defined accelerator configuration file defines everything about a
Composer design.
A user defines custom logic (CL) as functional units and wraps them using a "core"-like interface.
Sets of identical cores are called Composer Systems.
A top-level Composer design may contain many different systems.
Composer automates bus arbitration for commands, responses, and memory transactions.

In the above diagram, the user need only define the behavior of their CL in order to use it in software.

[Next (Composer Core)](c_core.md)
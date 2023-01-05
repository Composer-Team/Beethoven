# Scratchpads

[Up to Memory Subsystem](c_memory.md)

While users may manually declare and manipulate SRAM/BRAM/URAM segments using the Chisel `SyncReadMem` interface, we
provide a scratchpad utility for providing initialization from/writeback to memory. As well, getting large memory arrays
to pass timing can sometimes be challenging.

```scala
def getScratchpad(name: String):
(DecoupledIO[CScratchpadInitReq], CScratchpadAccessBundle, Bool)
```

Scratchpads are configured entirely within the accelerator configuration and are retrieved entirely by name.
Only one read and one write may be performed per cycle.
For discussion of scratchpad parameterization, refer to the [Configuration](c_config.md) section.
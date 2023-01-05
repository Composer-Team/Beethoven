# Writers

[Up to Memory Subsystem](c_memory.md)

```scala
def getSparseWriterModules(name: String,                            
                           useSoftwareAddressing: Boolean, 
                           dataBytes: Int, 
                           idx: Option[Int] = None):
(List[DecoupledIO[ChannelTransactionBundle]], List[WriterDataChannelIO])
```

The writer interface is pretty much exactly the same as the reader interface.
Notably, data can only be loaded in one data chunk at a time (no `vlen` option).
The same functionality can be accomplished, though, by just concatenating the array of data together
into a single datum.

[Next (Scratchpads)](c_scratchpad.md)
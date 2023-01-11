# Writers

[Up to Memory Subsystem](c_memory.md)

```scala
def getWriterModules(name: String,                            
                           useSoftwareAddressing: Boolean, 
                           dataBytes: Int, 
                           idx: Option[Int] = None):
(List[DecoupledIO[ChannelTransactionBundle]], List[WriterDataChannelIO])
```

`getWriterModules` returns two lists:
1. If `useSoftwareAddressing` is specified false, then the list of `ChannelTransactionBundle` is populated with the 
   transaction interfaces for the channels specified by `idx` and `name`. If `useSoftwareAddressing` is specified true,
   then the `ChannelTransactionBundle` list will be empty.
2. `WriterDataChannelIO` contains a decoupled interface for writing data. The width of the data channel is `dataBytes`
    bytes. `WriterDatachannelIO` also contains a signal `channelIdle` that is high when write transactions that have
    been issued are still in flight and is low when no transactions are in flight. In general, a user should not return
    a response to software from the FPGA until the channel has finished its transaction. Otherwise, stale data can be
   read by software.

[Next (Scratchpads)](c_scratchpad.md)
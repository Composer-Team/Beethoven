# Readers

[Up to Memory Subsystems](c_memory.md)

Reader modules are a read-only interface from CL to DRAM and are exposed via functions implemented in
[`ComposerCore.scala`](../Composer-Hardware/composer/src/main/scala/composer/ComposerCore.scala).

```scala
def getReaderModules(name: String,
                     useSoftwareAddressing: Boolean,
                     dataBytes: Int,
                     vlen: Int,
                     prefetchRows: Int = 0,
                     idx: Option[Int] = None):
(List[DecoupledIO[ChannelTransactionBundle]], List[DataChannelIO])
```

`getReaderModules` is the only way for CL to access readers.
Readers can be declared in the configuration file (discussed later) where they can be given a name.
A configuration file may, for instance, that there is a group of 16 parallel reader interfaces called "Matrix A".
Calling `getReaderModules("MatrixA", ...)`, the user fetches a list of 16 transaction interfaces and data interfaces.

### Transactions Interfaces

The transaction interface (`DecoupledIO[ChannelTransactionBundle]]`) allows users to issue reads for segments of memory.
The transaction is commmunicated over a ready/valid interface and is comprised of an address and a length (in bytes).

For some use-cases it may be desirable to do address computation in software. The composer software library provides
special "address" commands for this purpose, allowing the user to send an address to be used for a channel directly from
software to the channel. Whenever `useSoftwareAddressing` is specified, `getReaderModule` returns an empty list of
channel transaction bundles.

### Data Channel Interfaces

Once a transaction is underway, the data channel interface is used to access elements or groups of elements in sequential
order from that transaction.
`dataBytes` stipulates the width in bytes of a single datum and `vlen` stipulates how many datums to read per data
channel handshake.

### Prefetching

Reader modules without prefetching  read 64-bytes at a time from memory and only read more when those 64 bytes have been
read through the data channel. When using `prefetchRows > 0`, more data is fetched while data is consumed through the
data channel. Increasing the number of prefetch rows (64-byte chunks) may hide additional memory latencies but will
consume more resources.

### Individual channel parameterization

Without specifying `idx`, `getReaderModules` elaborates reader modules for every channel identified by `name`.
To parameterize channels under the same name differently, specify the index (0-indexed) for the channel within that group.

[Next (Writers)](c_writers.md)
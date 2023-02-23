# Scratchpads

[Up to Memory Subsystem](c_memory.md)

```scala
def getScratchpad(name: String): (CScratchpadInitReqIO, CScratchpadAccessBundle)
```

Like `getReaderModules(...)`, `getScratchpad` returns a tuple containing a request IO and a data access IO.
The `name` parameter corresponds to the `name` provided in the Config.

```scala
class CScratchpadInitReqIO(mem_out: TLBundle, nDatas: Int, maxTxLen: Int) extends Bundle {
  val progress = Output(UInt((log2Up(nDatas) + 1).W))
  val request = Flipped(Decoupled(new Bundle() {
    val memAddr = UInt(mem_out.params.addressBits.W)
    val scAddr = UInt(log2Up(nDatas).W)
    val len = UInt((log2Up(maxTxLen)+1).W)
  }))
}
```

`CScratchpadInitReqiO` is a bundle that contains IO to request a new transaction to loaded memory contents into the
scratchpad and a progress IO.
- `memAddr` - starting address for the memory read
- `scAddr` - scratchpad address for the memory contents to go into. Memory transactions with multiple elements in the read will go into the proceeding cells in the scratchpad.
- `len` - Length (in bytes) of the memory read
- `progress` - Current fill state (index) of the memory. Provided to allow early starts to kernels that can begin before the entire scratchpad is filled. 

```scala
class CScratchpadAccessBundle(scReqBits: Int, dataWidthBits: Int) extends Bundle {
  // note the flipped
  val readReq = Flipped(ValidIO(UInt(scReqBits.W)))
  val readRes = ValidIO(UInt(dataWidthBits.W))
  val writeReq = Flipped(ValidIO(new Bundle() {
      val addr = UInt(scReqBits.W)
      val data = UInt(dataWidthBits.W)
    }))
}
```

`CScratchpadAccessBundle` enables the user to access cells from the BRAM/URAM array

- `readReq` - address(index) and request valid bit driven by the user indicating which element to fetch from data array
- `readRes` - result of read corresponding to `readReq` after number of cycles dictated in the scratchpad configuration
- `writeReq` - only enabled if write supported in configuration
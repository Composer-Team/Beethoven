# Composer Core

[Up to Hardware](c_hardware.md)

## Introduction

[Code Link](../Composer-Hardware/composer/src/main/scala/composer/ComposerCore.scala)

Composer cores are the lowest level abstraction in the Composer framework and are the basis for implementing
user code.
By extending the `ComposerCore` class, the user module gains the necessary infrastructure for the core to communicate
the larger Composer system.

### Syntax

Extending the class is done like anything else. For this (and most examples in this documentation), we will be using
the `VectorAdder` example ([link](../Composer-Hardware/src/main/scala/design/Examples.scala)).

```scala
class VectorAdder(composerCoreParams: ComposerConstructor)(implicit p: Parameters)
  extends ComposerCore(composerCoreParams)
```

This is the most basic signature of a top-level CL - any top level module **must** extend ComposerCore and
have a `implicit p: Parameters` argument. 
A more complex example used throughout this documentation is a core that implements General Matrix Multiply (GeMM) ([link](../Composer-Hardware/src/main/scala/design/Gemm.scala)).

The GeMM core implementation takes in an optional additional parameters that contains information for parameterizing the
core itself.
Providing this functionality is important because one of the distinct strengths of Chisel over Verilog/VHDL is its
powerful parameterizability.

```scala
class GemmCore(composerCoreParams: ComposerConstructor, coreP: GemmParam)(implicit p: Parameters)
  extends ComposerCore(composerCoreParams)(p)
```

The GemmCore signature looks largely the same with the exception of the added core parameters.
In general, a ComposerCore implementation may have an arbitrary number of arguments in any order.
We discuss code linkage in the [Configuration](c_config.md) section.

### Request/Response Interface

Composer supports a request/response interface between the CL and software via the `io` symbol.
`io` is defined as a `ComposerCoreIO` which contains a read-only input `req` (request), write-only output `resp`(response), and a write-only output `busy` signal.

`req` is a `ComposerRoccCommand` which is comprised of a standard RoCC command, as well as 2 payloads that can be used
to carry user information from software to CL.

```scala
class ComposerRoccCommand()(implicit p: Parameters) extends Bundle {
  val inst = new Bundle {
    val rd = UInt(5.W)
    val rs1 = UInt(5.W)
    val rs2 = UInt(5.W)
    val xd = Bool()

    val xs1 = Bool()
    val xs2 = Bool()
    val opcode = UInt(7.W)

    val system_id = UInt(p(SystemIDLengthKey).W)
    val funct = UInt(3.W)
  }
  val core_id = UInt(p(CoreIDLengthKey).W)
  val payload1 = UInt((64-p(CoreIDLengthKey)-p(SystemIDLengthKey)).W)
  val payload2 = UInt(64.W)
}
```

Some of these fields depend on configuration parameters, namely system and core ID bits.
Reducing the number of bits used for system and core IDs increases the number of bits available
for payloads, but also reduces the number of addressable cores.
By default, CoreIDLength is 8 bits and SystemIDLength is 4.

The fields inside of `inst` besides `rs1` and `rs2` are used internally and the user should not attempt to use them for
core inputs. Instead, we suggest using the provided payloads to carry information necessary for executing a command.
`req` is also a ready/valid interface, requiring the user to define when it is ready to receive another request.

`resp` is a ready/valid interface ComposerRoccResponse.
CL must define when a response is valid. A response must obey the following behavior.
1. A response handshake must occur at least 1 cycle after a request was delivered to the core.
2. A core can only respond to a request that it was sent.
3. The request specifies an `xd` field. A reponse can only be sent when the request specifies `xd=1`. 
4. Only the `data` field of the ComposerRoccResponse may be driven by CL. Other fields are used for internal use.

```scala
class ComposerRoccResponse()(implicit p: Parameters) extends Bundle {
  val rd = UInt(5.W)
  val system_id = UInt(p(CoreIDLengthKey).W)
  val core_id = UInt(p(SystemIDLengthKey).W)
  val data = UInt((p(XLen)-system_id.getWidth-core_id.getWidth).W)
}
```

Responses are a 64-bit payload. For small payloads, 64-bits should be sufficient. Otherwise,
the response may be written to memory and a pointer can be returned in the response `data` payload.

[Next (Composer System)](c_memory.md)
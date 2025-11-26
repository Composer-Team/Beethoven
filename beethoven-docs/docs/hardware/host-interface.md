---
id: host-interface
title: Host Interface
sidebar_label: Host Interface
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Host Interface

Users specify host-facing interfaces with `BeethovenIO()`.
`BeethovenIO` takes in an `AccelCommand` and `AccelResponse` implementation and generates host C++ linkage for
communicating with the accelerator core. You can instantiate multiple `BeethovenIO()` and it will generate
multiple host C++ interfaces.

## AccelCommand

:::warning Type Restrictions
Stick to basic types (UInt, SInt, Bool, Address ≤128b) for reliable C++ code generation. Complex types may cause build issues.
:::

While we have supported arbitrary types inside `AccelCommand` in the past, maintaining the transformation between
arbitrary Chisel types and C++ is complex so we recommend using basic types for the most consistent results. The
recommended types are, `UInt`, `SInt`, `Bool`, and `Address`. These types may be at most 128b long. There is no
limit to the number of elements in the `AccelCommand`. We discuss memory allocation for the accelerator and the
associated `Address` type in the [Software Stack](/docs/software/overview/#beethoven-runtime) documentation.

Beethoven's host->HW interface is, for our current platforms, an 32-bit AXI-Lite port. For legacy reasons, we
encode commands using the RISC-V RoCC instruction format. RoCC instructions are a 32-bit instruction (which we
pack with routing information) and two 64-bit payloads. We pack the user-specified operands without fragmentation
into these payloads. Communicating a single instruction takes ~10µs over PCIE. Therefore, expect a multiple of
this delay for the number of 128-bit payloads necessary to communicate your `AccelCommand`.

:::note Communication Latency
Each 128-bit payload takes ~10µs over PCIe. Minimize command frequency for latency-sensitive applications.
:::

`AccelCommand` takes a name as input. This will be used to construct the C++ host binding for this command.
The accelerator will be accessible from host as `<Core-Name>::<Command-Name>`.

## AccelResponse

Responses are optional in Beethoven and are paired with a command. If a core does not respond to the core for
a given command, then the `BeethovenIO` does not need to specify a response. To return an empty acknowledgement
of completion for a command, you can use `EmptyAccelResponse()`.

Beethoven also allows you to return a response with a payload up to 64-bits wide. For longer payloads, we
recommend writing results to memory.

```scala title="AccelResponse with payload"
val my_io = BeethovenIO(...,
    AccelResponse(responseName) {
        ...
    })
```

The user provides a name for the accelerator response. This response will be the name of the response struct type.
For instance:

<Tabs>
<TabItem value="cmd" label="BeethovenIO" default>
```scala title="Defining a command with response"
// inside MyCore
val my_io = BeethovenIO(
    new AccelCommand("my_command"){...},
    new AccelResponse("my_response_t") {
        val a = UInt(4.W)
        val b = SInt(16.W)
    })
```
</TabItem>
<TabItem value="cpp" label="Generated C++">
```cpp title="Generated C++ interface"
namespace MyCore {
    beethoven::response_handle<my_response_t> my_command(...);

    struct my_response_t {
        uint8_t a;
        int16_t b;
    };
}
```
</TabItem>
</Tabs>

## Behavior of BeethovenIO

:::danger Protocol Violation
Never drive `req.ready` high without a corresponding response. This violates the protocol and causes host hangs.
:::

Both the command and response are coupled with ready/valid handshakes.
For the command, the user drives the ready signal and for the response, the user drives the valid signal.
The core should not drive the ready signal high until it has returned a corresponding response (if applicable).
The core may accept commands without a corresponding response while processing another command.
The core should not drive the response valid high while it is not processing a command.

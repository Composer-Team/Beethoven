# Composer Software Development

[Up to Index](index.md)

Composer provides its own FPGA/simulation management runtime to ease development and increase portability of user code.
Currently, we only offer C++ bindings, but these can easily be mapped into Python and other languages.
If, for whatever reason, you require C language bindings, please contact me and I can make any necessary changes to make
those available.

## FPGA Management - Composer Runtime

Direct FPGA management is handled entirely by
the [Composer-Runtime](https://github.com/Composer-Team/Composer_Verilator).
We currently only support Linux and Apple (M1 or x86) systems.
Building this tool requires the user to have built a hardware module and have the environment variable `COMPOSER_ROOT`
set to the root directory of the Composer repo.
Then, the user may build the tool.

The user must define `TARGET` for all builds and, when building for a real FPGA system, a `BACKEND` as well.

Currently supported `TARGET` values:

- `sim` - Fast Verilator-based simulator that does **not** simulate realistic memory access latencies. Traces are
  written out by default
- `vsim` - VSIM is the Vivado simulator. We currently use the F1 VSIM toolchain. Using this target can provide
  additional debugging details that may arise during real execution and not during the Verilator-based simulation.
  Notably, Verilator does not support high-impedence (Z) or undefined (X) values whereas VSim does. VSim is also much
  slower. In our tests, it takes around 30 minutes to run a single simulation run using VSim but <1 min to compile and
  run with our Verilator-based simulator.
- `fpga` - We currently only support the F1 FPGA backend but are currently developing support for the Kria FPGA. Please
  supply `-DBACKEND=F1` whenever using `-DTARGET=fpga`.
- `sanity_xsim` - Debugging backend. If you doubt that the Composer runtime is working correctly, please contact me
  directly.
- `sanity_fpga` - Similar to `sanity_xsim`

```shell

cd Composer-Runtime
mkdir build && cd build
cmake ../ -DTARGET=sim # set this to a valid TARGET value
make
./Composer-Runtime 
```

Only once the runtime is active can tests be run.

## Composer-Library

The Composer allows the user to interact with the Composer runtime and utilize the FPGA or simulation backends.
Composer aims to create an environment in which user code does not change at all between backends - the same code can
be used in simulation as well as in real FPGA deployment.

### Build and Install

```shell
cd Composer-Software
mkdir build && cd build
cmake ..
make
sudo make install
```

By default, the CMake script builds in Release mode.
If debug info within the library is required, you need only add the `-DCMAKE_BUILD_TYPE=Debug` option.
Installing as root user is recommended.
For non-root builds, some extra fidgeting may be required to help user executables find the library information.
If this is necessary, please contact me.
I can add an uninstall script if there is interest, though most of the installed files should be easy to manually.
On install (and reinstall), a list of all files is print to output.

### FPGA Setup

Currently, Composer has only been tested on single-FPGA systems. If this is a problem, please let me know and I can add
this functionality.
For single-FPGA systems, opening up a handle to a Composer Runtime instance is as simple as...

```cpp
#include <composer/fpga_handle.h>
#include <composer_allocator_declaration.h>

using namespace composer;

int main() {
  fpga_handle_t handle; // we can now use this to access our FPGA!
}
```

### Allocating FPGA Memory

Because of the heterogeneity of FPGA systems, it's hard to have a single memory allocation system that works in all
cases.
Consider an on-chip FPGA system that has a coherent interconnect with the CPU and shares the same DRAM DIMMs.
In that case, allocations made explicitly for reading and writing from the FPGA modules should be made by `malloc` to
ensure that the CPU does not erroneously allocate a section currently in use by the FPGA.
In another setup where the FPGA is a discrete accelerator (as in the case of the AWS F1 instances), the FPGA has its own
DRAM DIMMs entirely separate from the CPU.
Using `malloc` would be erroneous for several reasons, but fundamentally `malloc` allocates memory for use in the CPU
and the discrete FPGA DRAM will is completely independent from the software `malloc`.

For this reason, Composer provides an interface for allocating and freeing memory that adapts to the deployment
scenario.
Allocating is done similarly to normal implementations using `malloc` and `free`, except that it returns a
`composer::remote_ptr` object instead.

```cpp
// allocate chunk of memory for fpga use
remote_ptr fpga_handle_t::malloc(size_t len);
// free allocated memory chunk
void fpga_handle_t::free(&remote_ptr);
// copy memory in host address space to associated FPGA address
void fpga_handle_t::copy_to_fpga(&remote_ptr);
// copy memory in FPGA memory segment to host address
void fpga_handle_t::copy_from_fpga(&remote_ptr);

// access FPGA memory segment address
uint64_t remote_ptr::getFpgaAddr();
// access Host memory segment address
void * remote_ptr::getHostAddr();
```

A `remote_ptr` type has two important members: an FPGA address accessed via `getFpgaAddr()` and a host address
accessed via `getHostAddr()`.
A "Host" address is an allocation guaranteed to be accessible to the CPU software that stores a segment of memory that
may be transferred to the FPGA or contain data transferred from the FPGA.
The FPGA address is the address delivered to the FPGA guaranteed to be discrete from existing FPGA-bound memory
allocations and accessible from the Composer memory interfaces.
Should the user allocate more data than is accessible to the FPGA, an error will be raised.

Data can be moved between CPU and FPGA using the FPGA handle.

```cpp
fpga_handle_t handle;
auto my_alloc = handle.malloc(64);
memset(my_alloc.getHostAddr(), 0xAB, 64);
handle.copy_to_fpga(my_alloc);
// FPGA kernels called now will have access to the data written by memset via the FPGA address my_alloc.getFpgaAddr()
```

The user may explicitly construct the `remote_ptr` type in order to copy/move arbitrary segments.

```cpp
explicit remote_ptr(uint64_t fpgaAddr, void *hostAddr, uint32_t len);
// initialize host address to nullptr
explicit remote_ptr(uint64_t fpgaAddr, uint32_t len);
```

### Communicating with Cores

Composer uses the RoCC command interface to communicate with cores and provides an interface for constructing command
objects.

```cpp
rocc_cmd start_cmd(
    uint16_t system_id,
    uint8_t rs1_num,
    uint8_t rs2_num,
    bool expect_response,
    RD rd,
    uint8_t xs1,
    uint8_t xs2,
    uint8_t core_id,
    uint64_t rs1,
    uint64_t rs2);
```

"Start" commands are delivered to the system and core specified by `system_id` and `core_id`.
`system_id` is automatically generated when elaborating your Composer hardware design and are available when including
`#include <composer_allocator_declaration.h>`.
Instead of hard-coding these IDs, which may switch in between compilations, we recommend referencing the system by the
name chosen in the previously written configuration file as `<name>_ID`.
For instance, for a system with parameter `name="MySystem"`, the associated `system_id` is accessible via `MySystem_ID`.

`rs1_num`, `rs2_num`, `xs1`, `xs2`, `rs1`, and `rs2` do not have special semantic meaning and may be used by the user's core.
`rd` has special functionality for a subset of the values and so we provide an enum to ensure that the user selects a
value that does not cause unexpected behavior.

```c
  enum RD {
    /**
     * General purpose registers
     */
    R0 = 0,
    R1 = 1,
    R2 = 2,
    R3 = 3,
    R4 = 4,
    R5 = 5,
    R6 = 6,
    R7 = 7,
    R8 = 8,
    R9 = 9,
    R10 = 10,
    R11 = 11,
    R12 = 12,
    R13 = 13,
    R14 = 14,
    R15 = 15,
    /**
     * Special Registers
     **/
    AddressReadCnt = 16,
    AddressWriteCnt = 17,
    ReadCnt = 18,
    WriteCnt = 19,
    WriteResponseCnt = 20,
    ReadWait = 21,
    WriteWait = 22,
    /**
     * More general purpose registers
     */
    R23,
    R24,
    R25,
    R26,
    R27,
    R28,
    R29,
    R30,
    R31
  };
```

`expect_response` flag should be high if you intend for the core to return a response and low otherwise.
If `expect_response` is sent high and the response is never acknowledged, runtime resources will never be freed.

`rs1` and `rs2` correspond to the large payloads delivered to the core.
An error will be raised if these values are out of bounds.

A command can be sent by simply calling `.send()`.

```cpp
// can include via #include <composer/rocc_cmd.h>
response_handle rocc_cmd::send();
...

auto my_command = start_cmd(
    MySystem_ID, // system_id 
    0, // rs1_num
    0, // rs2_num
    false, // expect_response
    RD::R0, // rd
    0, // xs1
    0, // xs2
    0, // core_id
    0, // rs1
    0);// rs2
// send command to FPGA
my_command.send();
```

The `.send()` function returns a reponse handle that can be used to wait for a response from the command via `.get()`.
`.get()` returns a `rocc_response` type.
```cpp
// can include via #include <composer/response_handle.h>
rocc_response response_handle::get();
struct rocc_response {
  uint64_t data; // 52b payload!
  uint8_t core_id;
  uint8_t system_id;
  uint8_t rd;
}
```
```
auto my_command = // start command wqith expect_reponse = true
auto my_response_handle = my_command.send();
auto my_response = my_response_handle.get();
auto payload = my_response.
```

Pay special attention that the `data` payload inside of the `rocc_response` is only 52 bits! This can be increased up
to 62b by decreasing the maximum numbers of cores and systems inside of Composer.
To modify these parameters, use non-default parameters values when adding the `WithComposer()` configuration to your
Composer config.

```scala
// must use at least 1 bit for systemId and coreID 
class WithComposer(maximumTxLengthBytes: Int = 64, systemIDbits: Int = 4, coreIdBits: Int = 8) extends Config
```

### Communicating with Cores - Memory

Earlier in the [reader](c_readers.md) and [writer](c_writers.md) section, we discussed "software addressing" in which
software can directly provide a channel's transaction address and length.
Composer provides an "address command" interface to provide transaction information to these channels that have
software addressing enabled.

```cpp
rocc_cmd rocc_cmd::addr_cmd(ChannelAddressInfo info, const remote_ptr &ptr);
```
Create an address command using a `ChannelAddressInfo` and a `remote_ptr` struct.
An address command can be sent using the same `.send()` interface.
No response is expected from this command so using `.get()` is erroneous.
`ChannelAddressInfo` structs are generated using the following interfaces.

```
ChannelAddressInfo composer::getChannelSubIdx(uint16_t system_id, uint8_t core_id, ComposerChannels name, int id);
```
`getChannelSubIdx` is generated while building the Chisel module so it will not be visible to software until after the Composer hardware elaboration is completed.
- `system_id` - use in the same way as `start_cmd`
- `core_id` - use in the same way as `start_cmd`
- `name` - the Enum `ComposerChannels` is generated after building the Composer hardware project. It contains all of the names specified by the elaborated configuration. For a configuration with a channel group named "MyChannelsAAA", the channel is referenced via `ComposerChannels::MyChannelsAAA`.
- `id` - index for the channel within the channel group that you wish to send the command to

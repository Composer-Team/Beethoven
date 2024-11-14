import math
import sys


# Given a file `<name>.v` with topmodule <name>, output to text the
# IOs for that module as a Chisel bundle. All multi-bit inputs will
# be UInts, and all single-bit inputs will be Booleans.
def verilog_to_chisel_blackbox(file, ofile):
    with open(file, 'r') as f:
        lines = f.readlines()
    # Get the module name
    name = file.split('/')[-1].split('.')[0]
    # Get the IOs as pairs (name, width)
    inputs = []
    outputs = []
    for ln in lines:
        is_input = ln.find('input') != -1
        is_output = ln.find('output') != -1
        if not is_input and not is_output:
            continue
        width = 1
        if ln.find('[') != -1:
            width = int(ln.split('[')[1].split(':')[0]) + 1
        wire_name = ln.split(';')[0].split()[-1]
        if is_input:
            inputs.append((wire_name, width))
        else:
            outputs.append((wire_name, width))
    # Print the Chisel bundle
    with open(ofile, 'w') as f:
        f.write(f'''package design.machsuite.hls
import chisel3._
import chisel3.util._  
class HLSBB extends BlackBox {{
override val desiredName = "{name}"
val io = IO(new Bundle {{
''')
        for (name, width) in inputs:
            f.write(f'    val {name} = Input(UInt({width}.W))\n')
        for (name, width) in outputs:
            f.write(f'    val {name} = Output(UInt({width}.W))\n')
        f.write(f'  }})\n}}\n')
    return inputs, outputs


def generate_beethoven_harness_from_spec(io_pr, ofile, nm):
    inputs, outputs = io_pr
    # just look for memories and setup right now
    # memories are structed as <prefix>_[address, q, d, ce, we][<number>]
    # store memories as (prefix, <number> (None if not present))
    op_names = list(map(lambda x: x[0], outputs))
    print(outputs)
    memory_configs = []
    secondary_ready_conditions = []  # these need to be all high to start the module
    declarations = []
    io_defs = []

    attaches_and_state_machines = []

    for (name, w) in outputs:
        if "address" not in name:
            continue
        prefix = "_".join(name.split('_')[:-1])
        number = name.split("address")
        max_number = -1
        for (n, wp) in outputs:
            if f"{prefix}_address" in n:
                tnumber = n.split("address")[-1]
                if tnumber == "":
                    tnumber = -1
                else:
                    tnumber = tnumber[-1]
                max_number = max(max_number, int(tnumber))
        if len(number) == 1:
            number = None
        else:
            number = number[-1]
        has_write = f"{prefix}_d{number}" in op_names
        addr_width = w
        data_width = -1
        for (n, wp) in inputs:
            if n == f"{prefix}_q{number}":
                data_width = wp
                break
        if data_width == -1:
            print(inputs)
            print(outputs)
            print(f"Error: no data width found for {prefix}_q{number}")
            exit(1)

        if number == "0":
            memory_configs.append(f"""
        ScratchpadConfig(
          name = "{prefix}",
          dataWidthBits = {data_width},
          nDatas = {(2 ** addr_width)},
          nPorts = {max_number + 1}
        )""")
            io_defs.append(f"val {prefix}_address = Address()")
            secondary_ready_conditions.append(f"{prefix}_sp.requestChannel.init.ready")
            declarations.append(f"""val {prefix}_sp = getScratchpad("{prefix}")
{prefix}_sp.requestChannel.init.valid := io.req.fire
{prefix}_sp.requestChannel.init.bits.memAddr := io.req.bits.{prefix}_address
{prefix}_sp.requestChannel.init.bits.scAddr := 0.U
{prefix}_sp.requestChannel.init.bits.len := {(2 ** addr_width) * int(math.ceil(data_width / 8))}.U
when (io.req.fire) {{
  assert({prefix}_sp.requestChannel.init.ready)
}}
""")
        attaches_and_state_machines.append(f"""
{prefix}_sp.dataChannels({number}).req.valid := mod.io.{prefix}_ce{number}
{prefix}_sp.dataChannels({number}).req.bits.addr := mod.io.{prefix}_address{number}

{'//' if not has_write else ''}{prefix}_sp.dataChannels({number}).req.bits.write_enable := mod.io.{prefix}_we{number}
{'//' if has_write else ''}{prefix}_sp.dataChannels({number}).req.bits.write_enable := false.B

{'//' if not has_write else ''}{prefix}_sp.dataChannels({number}).req.bits.data := mod.io.{prefix}_d{number}
{'//' if has_write else ''}{prefix}_sp.dataChannels({number}).req.bits.data := DontCare

mod.io.{prefix}_q{number} := {prefix}_sp.dataChannels({number}).res.bits
""")
        # memories.append({
        #     "prefix": prefix,
        #     "number": number,
        #     "has_write": has_write,
        #     "d": f"{prefix}_d{number}" if has_write else None,
        #     "we": f"{prefix}_we{number}" if has_write else None,
        #     "q": f"{prefix}_q{number}",
        #     "ce": f"{prefix}_ce{number}",
        #     "address": f"{prefix}_address{number}",
        #     "hook_up":
        # })
    for name, w in inputs:
        if name[-2:] != "_i":
            continue
        if w <= 64:
            io_defs.append(f"val {name[:-2]} = UInt({w}.W)")
            attaches_and_state_machines.append(f"""
val {name[:-2]}_reg = Reg(UInt({w}.W))
when (io.req.fire) {{
    {name[:-2]}_reg := io.req.bits.{name[:-2]}
}}
mod.io.{name} := {name[:-2]}_reg
""")
        else:
            io_defs.append(f"val input_{name}_addr = Address()")
            declarations.append(f"""
assert({w} % 32 == 0)
val reg_{name} = Reg(Vec({w//32}, UInt(32.W)))
val wire_{name} = reg_{name}.asUInt
val ReaderModuleChannel(req_{name}, dat_{name}) = getReaderModule("{name}")
val sm_{name}_idle :: sm_{name}_mem :: Nil = Enum(2)
val state_{name} = RegInit(sm_{name}_idle)
dat_{name}.data.ready := false.B

req_{name}.bits.addr := io.req.bits.input_{name}_addr
req_{name}.bits.len := {w // 8}.U
req_{name}.valid := io.req.fire

val {name}_in_ctr = Reg(UInt(log2Up({w // 32}).W))
when (state_{name} === sm_{name}_idle) {{
    when (io.req.fire) {{
        state_{name} := sm_{name}_mem
        {name}_in_ctr := 0.U
    }}
}}.elsewhen (state_{name} === sm_{name}_mem) {{
    dat_{name}.data.ready := true.B
    when (dat_{name}.data.fire) {{
        reg_{name}({name}_in_ctr) := dat_{name}.data.bits
        {name}_in_ctr := {name}_in_ctr + 1.U
        when ({name}_in_ctr === {(w // 32) - 1}.U) {{
            state_{name} := sm_{name}_idle
        }}
    }}
}}
""")
            secondary_ready_conditions.append(f"(state_{name} === sm_{name}_idle)")
            attaches_and_state_machines.append(f"""mod.io.{name} := wire_{name}""")
            memory_configs.append(f"""
        ReadChannelConfig(
          name = "{name}",
          dataBytes = 4
)""")

    total_out_width = 0
    outs_to_join = []
    for (name, w) in outputs:
        if name[-2:] != "_o":
            continue
        declarations.append(f"val {name[:-2]} = Reg(UInt({w}.W))")
        attaches_and_state_machines.append(f"""
when (state === s_idle && mod.io.ap_done.asBool) {{
    {name[:-2]} := mod.io.{name}
}}""")
        outs_to_join.append(f"{name[:-2]}")
        total_out_width += w

    has_output = total_out_width > 0
    # create a state machine that will handle the output
    # We'll concatenate all the outputs into a single output
    # and then count through 32-bits at a time
    num_outs = total_out_width // 32
    if total_out_width % 32 != 0:
        num_outs += 1
        buff_amt = 32 - (total_out_width % 32)
        joined = f"Cat(0.U({buff_amt}.W), {', '.join(outs_to_join)})"
    else:
        joined = f"Cat({', '.join(outs_to_join)})"

    if has_output:
        io_defs.append("val outAddr = Address()")
        declarations.append(f"""
val reqOut_ready = Wire(Bool())
val s_idle :: s_cycle :: s_finish :: Nil = Enum(3)
val state = RegInit(s_idle)
val counter = Reg(UInt(log2Up({num_outs}).W))
""")
        attaches_and_state_machines.append(f'''
val join = {joined}
val split = splitIntoChunks(join, 32)
val WriterModuleChannel(reqOut, dOut) = getWriterModule("out") 
dOut.data.bits := split(counter)

dOut.data.valid := state === s_cycle
//reqOut.ready := state === s_idle
reqOut_ready := reqOut.ready
reqOut.bits.len := {num_outs * 4}.U
reqOut.bits.addr := io.req.bits.outAddr
reqOut.valid := io.req.valid

when (state === s_idle) {{
  when (mod.io.ap_done.asBool) {{
    state := s_cycle
    counter := 0.U
  }}
}}.elsewhen (state === s_cycle) {{
  when (dOut.data.ready) {{
    counter := counter + 1.U
    when (counter === {num_outs - 1}.U) {{
      state := s_finish
    }}
  }}
}}.elsewhen (state === s_finish) {{
  io.resp.valid := true.B
  when (io.resp.fire) {{
    state := s_idle
  }}
}}
''')
        memory_configs.append("""
        WriteChannelConfig(
          name = "out",
          dataBytes = 4,
        )
        """)
        out_ready = "reqOut_ready"
    else:
        declarations.append("val output_pulse = RegInit(false.B)")
        attaches_and_state_machines.append('''
        when (mod.io.ap_done) {{
            output_pulse := true.B
        }}
        io.resp.valid := output_pulse
        when (io.resp.fire) {{
            output_pulse := false.B
        }}
        ''')
        out_ready = "true.B"

    if len(secondary_ready_conditions) > 0:
        declarations.append("val start_machine = RegInit(false.B)")
        memories_are_done = " && ".join(secondary_ready_conditions)
        attaches_and_state_machines.append(f"""
val sm_idle :: sm_mem :: sm_fin :: Nil = Enum(3)
val sm_state = RegInit(sm_idle)
io.req.ready := sm_state === sm_idle && {out_ready}

when (sm_state === sm_idle) {{
  when (io.req.fire) {{
    sm_state := sm_mem
  }}
}}.elsewhen (sm_state === sm_mem) {{
  val mem_done = {memories_are_done}
  when (mem_done) {{
    sm_state := sm_fin
    start_machine := true.B
  }}
}}.elsewhen (sm_state === sm_fin) {{
  start_machine := false.B
  when (io.resp.fire) {{
    sm_state := sm_idle
  }}
}}
""")
        start_condition = "start_machine"
    else:
        start_condition = f"io.req.fire && {out_ready}"

    memory_configs_str = ",\n".join(memory_configs)
    # the other is start, clk, rst, done, idle, ready
    newline = '\n '
    with open(ofile, "w") as f:
        f.write(f"""
package design.machsuite.hls
import beethoven.Systems.AcceleratorCore
import beethoven.Parameters._
import beethoven.Generation.BeethovenBuild
import beethoven.common._
import chipsalliance.rocketchip.config.{{Config, Parameters}}
import chisel3._
import chisel3.util._

class HLSHarness()(implicit p: Parameters) extends AcceleratorCore() {{
  val io = BeethovenIO(new AccelCommand("{nm}") {{
    {newline.join(io_defs)}
  }}, new EmptyAccelResponse())
  os.walk(os.pwd / "hls").foreach {{ pth =>
    BeethovenBuild.addSource(pth)
  }}
  {newline.join(declarations)}  
    
  val mod = Module(new HLSBB)
  
  mod.io.ap_clk := clock.asBool
  mod.io.ap_rst := reset.asBool
  mod.io.ap_start := {start_condition}
  io.req.ready := mod.io.ap_ready.asBool && {out_ready}

   {newline.join(attaches_and_state_machines)}
}}
""")
    with open("HLSConfig.scala", "w") as f:
        f.write(
            f"""package design.machsuite.hls
import beethoven.Parameters._
import chipsalliance.rocketchip.config.Config
class HLSConfig(nCores: Int) extends Config((site, _, up) => {{
  case AcceleratorSystems => up(AcceleratorSystems, site) ++ Seq(
    AcceleratorSystemConfig(
      nCores = nCores,
      name = "{nm}",
      moduleConstructor = ModuleBuilder(p => new HLSHarness()(p)),
      memoryChannelConfig = List(
        {memory_configs_str}
      )))
  }})
""")
    with open("HLSRun.scala", "w") as f:
        f.write("""package design.machsuite.hls
import beethoven.Generation.BeethovenBuild
import beethoven.Parameters.WithBeethoven
import beethoven.Platforms.FPGA.Xilinx.KriaPlatform
import chipsalliance.rocketchip.config.Config

class HLSRun extends Config(new HLSConfig(1) ++ new WithBeethoven(
  platform = KriaPlatform()
))

object HLSRun extends BeethovenBuild(new HLSRun)
""")


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) != 2:
        print('Usage: verilogIO2chisel.py <file.v>')
        exit(1)
    q = verilog_to_chisel_blackbox(sys.argv[1], 'bb.scala')
    name = sys.argv[1].split('/')[-1].split('.')[0]
    generate_beethoven_harness_from_spec(q, 'ch.scala', name)
    exit(0)

import os
from typing import List
from VerilogUtils import *

HOME = os.environ['HOME']
EncryptTCLfname = HOME + "/bin/aws/src/encrypt.tcl"


def get_class(name: str):
    if name[:len(InterfacePrefixes.slave)] == InterfacePrefixes.slave:
        return PortClass.Slave
    elif name[:len(InterfacePrefixes.master)] == InterfacePrefixes.master:
        return PortClass.Master
    elif name[:len(InterfacePrefixes.DMA)] == InterfacePrefixes.DMA:
        return PortClass.DMA
    else:
        raise Exception


def scrape_aws_ports():
    with open(f"{HOME}/aws-fpga/hdk/common/shell_stable/design/interfaces/cl_ports.vh") as f:
        return scrape_ports_from_lines(f.readlines())


def scrape_cl_ports():
    ct = open(f"{HOME}/build-dir/generated-src/beethoven.sv")
    lns = []
    state = 0
    for ln in ct.readlines():
        if state == 0:
            if len(ln) < 6:
                continue
            spl = ln.split()
            if spl[0] == 'module':
                if spl[1][:-1] == 'BeethovenTop':
                    state = 1
        elif state == 1:
            # start scraping ios
            if ln[:2] == ');':
                lns.append(ln)
                break
            else:
                lns.append(ln)
    return scrape_ports_from_lines(lns)


def scrape_sh_ddr_ports():
    with open(f"{HOME}/aws-fpga/hdk/common/shell_stable/design/sh_ddr/sim/sh_ddr.sv") as f:
        lns = f.readlines()[45:]
        return scrape_ports_from_lines(lns)


def get_num_ddr_channels():
    with open(
            f"{HOME}/build-dir/generated-src/beethoven_allocator_declaration.h") as f:
        lns = f.readlines()
        for ln in lns:
            if "NUM_DDR_CHANNELS" in ln:
                return int(ln.strip().split()[-1])
        return -1


def bool_to_int(b):
    if b:
        return 1
    return 0


def search_for_part(part, prefix, part_list: List[VerilogPort]):
    matches = []
    for port in filter(lambda x: prefix in x.name, part_list):
        if "_" + part == port.name[-len(part) - 1:]:
            matches.append(port)
    return matches


wire_counter = 0


def declare_wire(g, width, ar_width):
    global wire_counter
    name = f"beethoven_{wire_counter}"
    wire_counter = wire_counter + 1
    return declare_wire_with_name(g, name, width, ar_width)


def declare_wire_with_name(g, name, width, ar_width):
    g.write('wire ')
    if width > 1:
        g.write(f"[{width - 1}:0] ")
    g.write(name)
    if ar_width > 1:
        g.write(f"[{ar_width - 1}:0]")
    g.write(";\n")
    return Wire(name, width, ar_width)


def declare_reg_with_name(g, name, width, ar_width):
    g.write('logic ')
    if width > 1:
        g.write(f"[{width - 1}:0] ")
    g.write(name)
    if ar_width > 1:
        g.write(f"[{ar_width - 1}:0]")
    g.write(";\n")
    return Reg(name, width, ar_width)


def write_aws_header(f):
    f.write(
        # f"`include \"beethoven.sv\"\n"
            f"`include \"cl_id_defines.vh\"\n"
            f"`ifndef BEETHOVEN_DEFINES\n"
            f"`define BEETHOVEN_DEFINES\n"
            f"`define CL_NAME beethoven_aws\n"
            f"`define FPGA_LESS_RST\n"
            f"`ifndef CL_VERSION\n"
            f"`define CL_VERSION 32'hee_ee_ee_00\n"
            f"`endif\n")
    # TODO this currently doesn't work for whatever reason, systemverilog doesn't see these defs
    for letter in ['A', 'B', 'D']:
        f.write(f"`ifndef DDR_{letter}_ABSENT\n"
                f"\t`define DDR_{letter}_PRESENT 1\n"
                f"`else\n"
                f"\t`define DDR_{letter}_PRESENT 0\n"
                f"`endif\n")
    f.write("`endif\n")


def create_aws_shell():
    # Get io_in and io_out ports for shell so that we can initialize them all to tied off values.

    # How many AXI4-Mem interfaces did we intialize Beethoven with?
    ndram = get_num_ddr_channels()

    ddr_ios: List[VerilogPort] = scrape_sh_ddr_ports()
    cl_ios: List[VerilogPort] = scrape_cl_ports()
    shell_ports: List[VerilogPort] = scrape_aws_ports()

    to_tie = []

    g = open("beethoven_aws.sv", 'w')
    # Write header
    write_aws_header(g)
    # Write module header
    g.write(
        f"module beethoven_aws #(parameter NUM_PCIE=1, parameter NUM_DDR=4, parameter NUM_HMC=4, parameter NUM_GTY=4)\n"
        f"(\n"
        f"\t`include \"cl_ports.vh\" // fixed ports definition included by build script\n"
        f");\n"
        f"logic pre_sync_rst_n;\n"
        f"logic sync_rst_n;\n"
        f"logic active_high_rst;\n"
        f"logic clk;\n"
        f"assign clk = clk_main_a0;\n"
        f"always_ff @(negedge rst_main_n or posedge clk)\n"
        f"\tif (!rst_main_n)\n"
        f"\tbegin\n"
        f"\t\tpre_sync_rst_n <= 0;\n"
        f"\t\tsync_rst_n <= 0;\n"
        f"\t\tactive_high_rst <= 1;\n"
        f"\tend\n"
        f"\telse\n"
        f"\tbegin\n"
        f"\t\tpre_sync_rst_n <= 1;\n"
        f"\t\tsync_rst_n <= pre_sync_rst_n;\n"
        f"\t\tactive_high_rst <= 0;\n"
        f"\tend\n")

    ############# INIT ALL BEETHOVEN STUFF ################
    cl_io_wiremap = {}
    cl_mems = {}
    axi_parts = set()
    # Find unique part classes
    for pr in cl_ios:
        if 'M' in pr.name:
            axi_parts.add(pr.get_axi_part_name())
    # Initialize list where all the underlying parts will live
    for part in axi_parts:
        cl_mems[part] = []
    # Put hte parts in their classes

    reserved_ddr_wires = ['sh_cl_ddr_is_ready']
    reserved_ddr_map = {}
    ddr_trained_ddrpart = search_for_part("is_ready", "ddr_", ddr_ios)[0]
    ddr_trained_ddrsig = declare_wire_with_name(g, "RESERVED_SH_DDR_WIRE_is_ready", ddr_trained_ddrpart.width,
                                                ddr_trained_ddrpart.ar_width)
    reserved_ddr_map.update({ddr_trained_ddrpart: ddr_trained_ddrsig})
    # collate the ddr_is_ready signals so we can throw them in BeethovenTop somewhere
    if ndram > 0:
        creadys = []
        if ndram >= 1:
            shell_sig_reg = declare_reg_with_name(g, "RESERVED_SHELL_is_ddr_ready", 1, 1)
            shell_sig_reg.assign(g, search_for_part("is_ready", "ddr_", shell_ports)[0])
            creadys.append(shell_sig_reg)
        if ndram > 1:
            for i in range(ndram - 1):
                shell_sig_reg = declare_reg_with_name(g, f"RESERVED_SH_DDR_is_ddr_ready{i}", 1, 1)
                shell_sig_reg.assign(g, ddr_trained_ddrsig.get_array_subwire(i))
                creadys.append(shell_sig_reg)
        for cr in creadys[1:]:
            creadys[0] = creadys[0] & cr
        dram_trained_signal = creadys[0]
    else:
        dram_trained_signal = Wire("1'b1", 1, 1)

    wnumber = 0
    for pr in cl_ios:
        wnumber += 1
        if pr.name in ['clock', 'reset']:
            continue
        pc = get_class(pr.name)
        apn = pr.get_axi_part_name()
        wr = declare_wire_with_name(g, f"beethoven_{pc.name}{wnumber}_{apn}", pr.width, pr.ar_width)
        # find wires in the group and fuse them together
        cl_io_wiremap.update({pr: wr})
        if get_class(pr.name) == PortClass.Master:
            a = cl_mems[pr.get_axi_part_name()]
            cl_mems[pr.get_axi_part_name()] = a + [wr]
    # Shape the parts into the same shape as the ddr ports
    ddr_axis = {}
    testy = list(map(lambda x: x.name, ddr_ios))
    for ddr in ddr_ios:
        axi_name = ddr.get_axi_part_name()
        if ddr.is_ddr_pin():
            if ddr.name in reserved_ddr_wires:
                continue
            if ddr.ar_width == 1 and ddr.width > 1:
                ddr_wire = [declare_wire_with_name(g, f"beethoven_ddr_{i}_{axi_name}", 1, 1)
                            for i in range(ddr.width)]
            else:
                ddr_wire = [declare_wire_with_name(g, f"beethoven_ddr_{i}_{axi_name}", ddr.width, 1)
                            for i in range(ddr.ar_width)]
            ddr_fuse = declare_wire_with_name(g, f"beethoven_ddr_fuse_{axi_name}", ddr.width,
                                              ddr.ar_width)
            for i, w in enumerate(ddr_wire):
                if ddr.input:
                    ddr_fuse.get_array_subwire(i).assign(g, w)
                else:
                    w.assign(g, ddr_fuse.get_array_subwire(i))

            ddr_axis.update({axi_name: ddr_fuse})
            if cl_mems.get(axi_name) is None and ddr.input:
                continue
            # Find parts to bind to from CL / shell
            ports = cl_mems[ddr.get_axi_part_name()]
            assert ports is not None
            if len(ports) == 0:
                break
            # we use shell ports first (only sh_ddr for 2nd 3rd 4th dimm)

            if len(ports) >= 1:
                # hook up the shell DDR_C port to the first port
                shell_port = search_for_part(axi_name, "ddr_", shell_ports)
                assert len(shell_port) == 1
                shell_port = shell_port[0]
                if shell_port.input:
                    if axi_name in ['awready', 'arready']:
                        shell_port = shell_port & dram_trained_signal
                    ports[0].assign(g, shell_port)
                else:
                    shell_port.assign(g, ports[0])
            else:
                if ddr.input:
                    ddr_wire[0].tie_off(g)

            ports = ports[1:]
            ports = ports + (3 - len(ports)) * [None]
            # do the rest of the sh_ddr ports
            for i, port in enumerate(ports):
                if port is None:
                    if ddr.input:
                        ddr_wire[i].tie_off(g)
                else:
                    if ddr.output:
                        if axi_name in ['awready', 'arready']:
                            to_assign = ddr_wire[i] & dram_trained_signal
                        else:
                            to_assign = ddr_wire[i]
                        port.assign(g, to_assign)
                    else:
                        ddr_wire[i].assign(g, port)

    # Connect the Slave AXIL ports
    for clio in cl_io_wiremap.keys():
        wi = cl_io_wiremap[clio]
        pc = get_class(clio.name)
        if pc != PortClass.Slave:
            continue
        p = search_for_part(clio.get_axi_part_name(), "ocl", shell_ports)
        if len(p) == 0:
            if clio.input:
                wi.tie_off(g)
            continue
        p = p[0]
        if p.input:
            wi.assign(g, p)
        else:
            p.assign(g, wi)

    for dma in filter(lambda x: 'dma' in x.name, cl_ios):
        # find matching beethoven logic port
        p = search_for_part(dma.get_axi_part_name(), "dma_pcis", shell_ports)
        if len(p) == 0:
            if dma.input:
                cl_io_wiremap[dma].tie_off(g)
                continue
            else:
                continue
        if dma.input:
            cl_io_wiremap[dma].assign(g, p[0])
        else:
            p[0].assign(g, cl_io_wiremap[dma])

    g.write("BeethovenTop myTop(\n"
            "\t.clock(clk),\n"
            "\t.reset(active_high_rst),\n")
    for i, pr in enumerate(cl_ios):
        g.write(f"\t.{pr.name}({cl_io_wiremap[pr].name})")
        if i == len(cl_ios) - 1:
            g.write("\n")
        else:
            g.write(",\n")
    g.write(');\n')

    # Instantiate SH_DDR module
    g.write(f"// DDR controller instantiation\n"
            f"sh_ddr #(.DDR_A_PRESENT({bool_to_int(ndram > 1)}),"
            f" .DDR_B_PRESENT({bool_to_int(ndram > 2)}),"
            f" .DDR_D_PRESENT({bool_to_int(ndram > 3)}))\n"
            f"\tSH_DDR(\n"
            f".clk(clk),\n"
            f".rst_n(sync_rst_n),\n"
            f".stat_clk(clk),\n"
            f".stat_rst_n(sync_rst_n),\n")
    # Now we add DDR ports
    for port in ddr_ios:
        if port.name[:2] == 'M_' or 'CLK' in port.name or 'RST' in port.name:
            continue
        if 'stat' in port.name:
            # find opposing port in shell
            p = search_for_part(port.get_stat_name(), 'ddr', shell_ports)
            assert len(p) == 1
            p = p[0]
            if p.output or p.inout:
                g.write(f".{port.name}({p.name}),\n")
            else:
                g.write(f".{p.name}({port.name}),\n")
            continue
        assert not port.inout
        if port.name in reserved_ddr_wires:
            g.write(f".{port.name}({reserved_ddr_map[port].name}),\n")
            continue
        fuse = ddr_axis[port.get_axi_part_name()]
        assert fuse is not None
        g.write(f".{port.name}({fuse.name}),\n")
    # write signals that go straight to shell (DDR pins)
    for letter, number in [('A', '0'), ('B', '1'), ('D', '3')]:
        if letter != 'A':
            g.write(",\n")
        g.write(f".CLK_300M_DIMM{number}_DP(CLK_300M_DIMM{number}_DP),\n"
                f".CLK_300M_DIMM{number}_DN(CLK_300M_DIMM{number}_DN),\n"
                f".M_{letter}_ACT_N(M_{letter}_ACT_N),\n"
                f".M_{letter}_MA(M_{letter}_MA),\n"
                f".M_{letter}_BA(M_{letter}_BA),\n"
                f".M_{letter}_BG(M_{letter}_BG),\n"
                f".M_{letter}_CKE(M_{letter}_CKE),\n"
                f".M_{letter}_ODT(M_{letter}_ODT),\n"
                f".M_{letter}_CS_N(M_{letter}_CS_N),\n"
                f".M_{letter}_CLK_DN(M_{letter}_CLK_DN),\n"
                f".M_{letter}_CLK_DP(M_{letter}_CLK_DP),\n"
                f".M_{letter}_PAR(M_{letter}_PAR),\n"
                f".M_{letter}_DQ(M_{letter}_DQ),\n"
                f".M_{letter}_ECC(M_{letter}_ECC),\n"
                f".M_{letter}_DQS_DP(M_{letter}_DQS_DP),\n"
                f".M_{letter}_DQS_DN(M_{letter}_DQS_DN),\n"
                f".cl_RST_DIMM_{letter}_N(cl_RST_DIMM_{letter}_N)")
    g.write(");\n")
    list(filter(lambda x: x.name == 'cl_sh_id0', shell_ports))[0].assign_constant(g, "`CL_SH_ID0")
    list(filter(lambda x: x.name == 'cl_sh_id1', shell_ports))[0].assign_constant(g, "`CL_SH_ID1")
    list(filter(lambda x: x.name == 'cl_sh_status1', shell_ports))[0].assign_constant(g, "`CL_VERSION")
    g.write("// begin tie-offs\n")
    for pwire in shell_ports:
        lower = pwire.name.lower()
        if pwire.name[:2] == 'M_' or lower.find('ddr') != -1 \
                or lower.find('ocl') != -1 or lower.find('clk') != -1 or lower.find('rst') != -1:
            continue
        if 'ack' in lower:
            set_to = "1"
        else:
            set_to = "0"

        if pwire.output and pwire.occupancy < pwire.ar_width:
            pwire.tie_off(g, set_to)

    g.write("// begin secondary tie-offs\n")
    # Do tie-offs

    g.write("\nendmodule\n")

    g.close()


def write_id_defines():
    with open("design/cl_id_defines.vh", 'w') as f:
        f.write("`define CL_NAME beethoven_aws\n"
                "`define CL_SH_ID0 32'hF001_1D0F\n"
                "`define CL_SH_ID1 32'h1D51_FEDC\n")


def write_encrypt_script():
    with open(EncryptTCLfname) as f:
        lns = f.readlines()

    to_write = ["file copy -force $CL_DIR/design/beethoven_aws.sv $TARGET_DIR\n",
                "file copy -force $CL_DIR/design/cl_id_defines.vh $TARGET_DIR\n"] + \
               [f"file copy -force $CL_DIR/design/{x} $TARGET_DIR\n"
                for x in list(os.walk(f"{HOME}/build-dir/generated-src/"))[0][2]]

    with open("build/scripts/encrypt.tcl", 'w') as f:
        for ln in lns:
            if "file copy" in ln:
                if to_write is not None:
                    for tw in to_write:
                        f.write(tw)
                    to_write = None
            elif "-lang verilog" in ln:
                f.write(
                    "encrypt -k $HDK_SHELL_DIR/build/scripts/vivado_keyfile_2017_4.txt -lang verilog  [glob -nocomplain -- $TARGET_DIR/*.{v,sv,vh,inc}]\n")
            else:
                f.write(ln)

def create_synth_script():
    with open(f"{HOME}/bin/aws/src/synth.tcl") as i:
        lns = i.readlines()
        whole_file = ""
        for q in lns:
            whole_file = whole_file + q

    with open("build/scripts/synth.tcl", 'w') as o:
        src_list = ""
        for src in ["beethoven_aws.sv"
            # , "beethoven.sv"
                    ]:
            src_list = src_list + f"\t{os.getcwd()}/design/{src} \\\n"
        whole_file = whole_file.replace("SOURCE_LIST_GOES_HERE", src_list)
        o.write(whole_file)


def copy_dcp_scripts():
    os.system(f"cp {HOME}/bin/aws/src/*dcp* build/scripts/")


def move_sources_to_design():
    os.system(f"cp -r generated-src/* design/")
    with open("design/beethoven_aws.sv", "a") as f:
        with open("generated-src/beethoven.sv", "r") as f2:
            f.write(f2.read())

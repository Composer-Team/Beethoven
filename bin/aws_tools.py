import os
from typing import List
from enum import Enum


# This can change from time to time, so define here and use enum instead within code
class InterfacePrefixes:
    slave = "S"
    master = "M"
    DMA = "dma"


class PortClass(Enum):
    Slave = 0
    Master = 1
    DMA = 2


def get_fp_sources():
    if os.path.exists(f"{os.environ['COMPOSER_ROOT']}/Composer-Hardware/.fpnew_cache"):
        files = list(os.walk(f"{os.environ['COMPOSER_ROOT']}/Composer-Hardware/.fpnew_cache/"))[0][2]
        return list(filter(lambda x: ('yosys' not in x) and ('preprocessed' not in x) and ('.v' in x) and
                                     ('filtered' not in x), files))
    else:
        return list()


def get_class(name: str):
    if name[:len(InterfacePrefixes.slave)] == InterfacePrefixes.slave:
        return PortClass.Slave
    elif name[:len(InterfacePrefixes.master)] == InterfacePrefixes.master:
        return PortClass.Master
    elif name[:len(InterfacePrefixes.DMA)] == InterfacePrefixes.DMA:
        return PortClass.DMA
    else:
        raise Exception


def is_number(q):
    # noinspection PyBroadException
    try:
        a = int(q)
    except:
        return False
    return True


def extract(s, p):
    assert p in s
    idx = s.find(p)
    return s[:idx] + s[idx + len(p):]


class Wire:
    def __init__(self, name, width, ar_width):
        self.name = name
        self.width = width
        self.ar_width = ar_width
        self.occupancy = 0
        self.assignment = []

    def __hash__(self):
        return self.name.__hash__()

    def assign(self, g, operand):
        assert self.occupancy < self.ar_width
        assert operand.ar_width == 1
        self.assignment.append(operand)
        assert self.ar_width == 1
        op1 = self.name
        # Dont' overassign
        if operand.width < self.width:
            op2 = '{' + f"{self.width - operand.width}'b0, {operand.name}" + "}"
        elif self.width < operand.width:
            op2 = f"{operand.name}[{self.width - 1}:0]"
        else:
            op2 = operand.name

        g.write(f"assign {op1} = {op2};\n")
        self.occupancy += 1

    def assign_array(self, g, op):
        g.write(f"assign {self.name} = {op.name};\n")

    def get_array_subwire(self, i):
        if self.ar_width > 1:
            return Wire(f"{self.name}[{i}]", self.width, 1)
        else:
            return Wire(f"{self.name}[{i}]", 1, 1)

    def __eq__(self, other):
        return self.name == other.name

    def is_ddr_pin(self):
        return 'sh_cl' in self.name or 'cl_sh' in self.name

    def tie_off(self, g, special_val="0"):
        g.write(f"assign {self.name} = ")
        tieoff = "0"
        if special_val == '1':
            tieoff = '1' * self.width
        if self.ar_width == 1:
            g.write(f"{self.width}'b{tieoff};\n")
        else:
            g.write("'{")
            for i in range(self.ar_width):
                g.write(f"{self.width}'b{tieoff}, ")
            g.write("};\n")

    def __and__(self, other):
        assert other.ar_width == 1 and self.ar_width == 1
        assert other.width == self.width
        return Wire(f"({self.name} & {other.name})", self.width, 1)


class VerilogPort(Wire):
    def __init__(self, name: str, width: int, ar_len: int, io_type: str, is_logic: bool):
        super().__init__(name, width, ar_width=ar_len)
        if 'bits_' in name:
            idx = name.find('bits_')
            self.axi_clean_name = name[:idx] + name[idx + len('bits_'):]
        else:
            self.axi_clean_name = name
        self.input = io_type == 'input'
        self.output = io_type == 'output'
        self.inout = io_type == 'inout'
        self.logic = is_logic
        assert self.input or self.output or self.inout

    def get_group_name(self):
        if not '_' in self.axi_clean_name:
            return None
        else:
            return self.axi_clean_name[:self.axi_clean_name.find('_')]

    def get_axi_part_name(self):
        return self.axi_clean_name.split('_')[-1]

    def is_stat(self):
        return 'ddr' in self.axi_clean_name and 'stat' in self.axi_clean_name

    def get_stat_name(self):
        return self.axi_clean_name.split('_')[-1]

    def __hash__(self):
        return self.name.__hash__()

    def assign(self, g, operand):
        assert self.output
        super().assign(g, operand)

    def assign_constant(self, g, val_str):
        assert self.output
        super().assign(g, Wire(val_str, self.width, self.ar_width))


class Reg(Wire):
    def assign(self, g, operand: Wire):
        assert self.occupancy < self.ar_width
        assert operand.ar_width == 1
        self.assignment.append(operand)
        assert self.ar_width == 1
        op1 = self.name
        # Dont' overassign
        if operand.width < self.width:
            op2 = '{' + f"{self.width - operand.width}'b0, {operand.name}" + "}"
        elif self.width < operand.width:
            op2 = f"{operand.name}[{self.width - 1}:0]"
        else:
            op2 = operand.name
        g.write(f"always_ff @(posedge clk)\n"
                f"begin\n"
                f"\t{op1} <= {op2};\n"
                f"end\n")
        self.occupancy += 1


def scrape_ports_from_lines(lns):
    ports = []
    lns_fresh = map(lambda x: x.strip().replace(',', '').replace('wire', ''), lns)
    lns_filt = []
    filter_stack = []

    def can_consume():
        return '/*' not in filter_stack and '`ifdef' not in filter_stack

    for ln in lns_fresh:
        print(ln)
        found_comment = False
        if '/*' in ln:
            filter_stack.append('/*')
            ln = ln[ln.find('/*')+2:]
            found_comment = True
            print('d')
        if '*/' in ln:
            assert filter_stack[-1] == '/*'
            filter_stack = filter_stack[:-1]
            found_comment = False
            print('e')
        if found_comment:
            continue
        if '`ifdef' in ln:
            filter_stack.append('`ifdef')
            print('c')
            continue
        if '`ifndef' in ln:
            filter_stack.append('`ifndef')
            print('b')
            continue
        if '`endif' in ln:
            assert filter_stack[-1] == '`ifndef' or filter_stack[-1] == '`ifdef'
            filter_stack = filter_stack[:-1]
            print('a')
            continue
        if '`define' in ln:
            print("found define")
            continue

        if not can_consume():
            print(f"skipping {ln}")
            continue
        if ");" in ln:
            print("ending reading, found " + ln)
            break
        lns_filt.append(ln)
        pass

    print('')
    for ln in lns_filt:
        lncopy = ln
        if 'NUM_GTY' in ln:
            raise Exception("AHH")
        # remove everything after comments
        if '//' in ln:
            ln = ln[:ln.find('//')].strip()
        # if it's empty, remove now
        if ln == '':
            continue
        if ");" in ln:
            return ports
        if 'input' in ln:
            io_ty = 'input'
            ln = extract(ln, 'input')
        elif 'output' in ln:
            io_ty = 'output'
            ln = extract(ln, 'output')
        elif 'inout' in ln:
            io_ty = 'inout'
            ln = extract(ln, 'inout')
        else:
            raise Exception("Unrecognized port type in " + ln)

        is_logic = 'logic' in ln
        if is_logic:
            ln = extract(ln, 'logic')

        name_str = str(ln.replace('input', '').replace('output', '').strip())
        found_start = False
        found_end = False
        name_start = -1
        name_end = -1
        for i, c in enumerate(name_str):
            c = str(c)
            if not found_start:
                if c.isalpha():
                    found_start = True
                    name_start = i
                    continue
            elif found_start and not found_end:
                if not c.isalnum() and c != '_':
                    found_end = True
                    name_end = i
                    continue
        if name_end != -1:
            name = name_str[name_start:name_end]
        else:
            name = name_str[name_start:]

        # Find width
        before_name = name_str[:name_start]
        if '[' in before_name:
            n = before_name[before_name.find('[') + 1:before_name.find(':')]
            if not is_number(n):
                n = 0
            width = 1 + int(n)
        else:
            width = 1

        # Find ar_width
        after_name = name_str[name_end:]
        if '[' in after_name:
            ar_width = 1 + int(after_name[after_name.find('[') + 1:after_name.find(':')])
        else:
            ar_width = 1
        # if 'bits_' in name:
        #     name = name[:name.find('bits_')] + name[name.find('bits_') + 5:]

        if 'rst_' in name or 'reset' in name or 'clk' in name or 'clock' in name:
            continue
        ports.append(VerilogPort(name, width, ar_width, io_ty, is_logic))
    return ports


def scrape_aws_ports():
    with open(f"{os.environ['COMPOSER_ROOT']}/aws-fpga/hdk/common/shell_stable/design/interfaces/cl_ports.vh") as f:
        return scrape_ports_from_lines(f.readlines())


def scrape_cl_ports():
    ct = open(f"{os.environ.get('COMPOSER_ROOT')}/Composer-Hardware/vsim/generated-src/composer.v")
    lns = []
    state = 0
    for ln in ct.readlines():
        if state == 0:
            if len(ln) < 6:
                continue
            spl = ln.split()
            if spl[0] == 'module':
                if spl[1][:-1] == 'ComposerTop':
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
    with open(f"{os.environ['COMPOSER_ROOT']}/aws-fpga/hdk/common/shell_stable/design/sh_ddr/sim/sh_ddr.sv") as f:
        lns = f.readlines()[45:]
        return scrape_ports_from_lines(lns)


def get_num_ddr_channels():
    with open(
            f"{os.environ['COMPOSER_ROOT']}/Composer-Hardware/vsim/generated-src/composer_allocator_declaration.h") as f:
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
            print(f"{part} matches in {port.name}")
            matches.append(port)
    return matches


wire_counter = 0


def declare_wire(g, width, ar_width):
    global wire_counter
    name = f"composer_{wire_counter}"
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
    f.write(f"`include \"composer.v\"\n"
            f"`include \"cl_id_defines.vh\"\n"
            f"`ifndef COMPOSER_DEFINES\n"
            f"`define COMPOSER_DEFINES\n"
            f"`define CL_NAME composer_aws\n"
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

    # How many AXI4-Mem interfaces did we intialize Composer with?
    ndram = get_num_ddr_channels()

    ddr_ios: List[VerilogPort] = scrape_sh_ddr_ports()
    cl_ios: List[VerilogPort] = scrape_cl_ports()
    shell_ports: List[VerilogPort] = scrape_aws_ports()

    for pr in cl_ios:
        print(f"name: {pr.name}")

    to_tie = []

    g = open("composer_aws.sv", 'w')
    # Write header
    write_aws_header(g)
    # Write module header
    g.write(
        f"module composer_aws #(parameter NUM_PCIE=1, parameter NUM_DDR=4, parameter NUM_HMC=4, parameter NUM_GTY=4)\n"
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

    ############# INIT ALL COMPOSER STUFF ################
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
    # collate the ddr_is_ready signals so we can throw them in ComposerTop somewhere
    if ndram > 0:
        creadys = []
        if ndram >= 1:
            shell_sig_reg = declare_reg_with_name(g, "RESERVED_SHELL_is_ddr_ready", 1, 1)
            shell_sig_reg.assign(g, search_for_part("is_ready", "ddr_", shell_ports)[0])
            creadys.append(shell_sig_reg)
        if ndram > 1:
            for i in range(ndram-1):
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
        wr = declare_wire_with_name(g, f"composer_{pc.name}{wnumber}_{apn}", pr.width, pr.ar_width)
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
                ddr_wire = [declare_wire_with_name(g, f"composer_ddr_{i}_{axi_name}", 1, 1)
                            for i in range(ddr.width)]
            else:
                ddr_wire = [declare_wire_with_name(g, f"composer_ddr_{i}_{axi_name}", ddr.width, 1)
                            for i in range(ddr.ar_width)]
            ddr_fuse = declare_wire_with_name(g, f"composer_ddr_fuse_{axi_name}", ddr.width,
                                              ddr.ar_width)
            for i, w in enumerate(ddr_wire):
                if ddr.input:
                    ddr_fuse.get_array_subwire(i).assign(g, w)
                else:
                    w.assign(g, ddr_fuse.get_array_subwire(i))

            ddr_axis.update({axi_name: ddr_fuse})
            if cl_mems.get(axi_name) is None and ddr.input:
                print(f"Skipping part {ddr.name}. We think it's an AXI3 interface...")
                continue
            # Find parts to bind to from CL / shell
            ports = cl_mems[ddr.get_axi_part_name()]
            assert ports is not None
            if len(ports) == 0:
                print("no ports found matching " + axi_name)
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
        # find matching composer logic port
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

    g.write("ComposerTop myTop(\n"
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
        print(lower)
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
        f.write("`define CL_NAME composer_aws\n"
                "`define CL_SH_ID0 32'hF001_1D0F\n"
                "`define CL_SH_ID1 32'h1D51_FEDC\n")


def write_encrypt_script_from_base_inline(fname, ):
    with open(fname) as f:
        lns = f.readlines()
    to_write = ["file copy -force $CL_DIR/design/composer_aws.sv $TARGET_DIR\n",
                "file copy -force $CL_DIR/design/composer.v $TARGET_DIR\n",
                "file copy -force $CL_DIR/design/cl_id_defines.vh $TARGET_DIR\n"] +\
               [f"file copy -force $CL_DIR/design/{x} $TARGET_DIR\n" for x in get_fp_sources()]
    with open(fname, 'w') as f:
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


def create_synth_script(oname):
    with open(f"{os.environ['COMPOSER_ROOT']}/aws-fpga/hdk/cl/examples/cl_dram_dma/build/scripts/"
              f"synth_cl_dram_dma.tcl") as f:
        lns = f.readlines()
    with open(oname, 'w') as g:
        for ln in lns:
            if "glob $ENC_SRC" in ln:
                g.write(f"read_verilog -sv [glob {os.getcwd()}/design/*v]")
            elif "*.?v" in ln:
                idx = ln.find("*.?v")
                g.write(ln[:idx] + "*v" + ln[idx + 4:])
            elif "close_project" in ln:
                g.write("report_power -file power_report.txt\nreport_utilization -hierarchical -file utilization_report.txt\n" + ln)
            else:
                g.write(ln)


def create_dcp_script_inline(fname):
    os.system(f"sed -i.bu 's/cl_hello_world/composer_aws/g' {fname}")


def move_sources_to_design():
    os.system(f"cp generated-src/composer.v design/")
    for src in get_fp_sources():
        os.system(f"cp {os.environ['COMPOSER_ROOT']}/Composer-Hardware/.fpnew_cache/{src} design/")


from enum import Enum


def is_number(q):
    # noinspection PyBroadException
    try:
        a = int(q)
    except Exception:
        return False
    return True


# This can change from time to time, so define here and use enum instead within code
class InterfacePrefixes:
    slave = "S"
    master = "M"
    DMA = "dma"


class PortClass(Enum):
    Slave = 0
    Master = 1
    DMA = 2


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


def extract(s, p):
    assert p in s
    idx = s.find(p)
    return s[:idx] + s[idx + len(p):]


def scrape_ports_from_lines(lns):
    ports = []
    lns_fresh = map(lambda x: x.strip().replace(',', '').replace('wire', ''), lns)
    lns_filt = []
    filter_stack = []

    def can_consume():
        return '/*' not in filter_stack and '`ifdef' not in filter_stack

    for ln in lns_fresh:
        found_comment = False
        if '/*' in ln:
            filter_stack.append('/*')
            ln = ln[ln.find('/*')+2:]
            found_comment = True
        if '*/' in ln:
            assert filter_stack[-1] == '/*'
            filter_stack = filter_stack[:-1]
            found_comment = False
        if found_comment:
            continue
        if '`ifdef' in ln:
            filter_stack.append('`ifdef')
            continue
        if '`ifndef' in ln:
            filter_stack.append('`ifndef')
            continue
        if '`endif' in ln:
            assert filter_stack[-1] == '`ifndef' or filter_stack[-1] == '`ifdef'
            filter_stack = filter_stack[:-1]
            continue
        if '`define' in ln:
            continue
        if not can_consume():
            continue
        if ");" in ln:
            break
        lns_filt.append(ln)
        pass

    for ln in lns_filt:
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

import os

"""
ERROR: [Synth 8-1031] DDR_A_PRESENT is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:503]
ERROR: [Synth 8-1031] DDR_B_PRESENT is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:504]
ERROR: [Synth 8-1031] DDR_D_PRESENT is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:505]
ERROR: [Synth 8-1031] cl_sh_pcis_awready is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:637]
ERROR: [Synth 8-1031] cl_sh_pcis_wready is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:639]
ERROR: [Synth 8-1031] cl_sh_pcis_bresp is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:641]
ERROR: [Synth 8-1031] cl_sh_pcis_bid is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:642]
ERROR: [Synth 8-1031] cl_sh_pcis_bvalid is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:643]
ERROR: [Synth 8-1031] cl_sh_pcis_arready is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:645]
ERROR: [Synth 8-1031] cl_sh_pcis_rdata is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:647]
ERROR: [Synth 8-1031] cl_sh_pcis_rresp is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:648]
ERROR: [Synth 8-1031] cl_sh_pcis_rid is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:649]
ERROR: [Synth 8-1031] cl_sh_pcis_rlast is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:650]
ERROR: [Synth 8-1031] cl_sh_pcis_rvalid is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:651]
ERROR: [Synth 8-1751] cannot index into non-array cl_sh_pcim_awvalid [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:658]
ERROR: [Synth 8-1751] cannot index into non-array cl_sh_pcim_wlast [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:662]
ERROR: [Synth 8-1751] cannot index into non-array cl_sh_pcim_wvalid [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:663]
ERROR: [Synth 8-1751] cannot index into non-array cl_sh_pcim_bready [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:665]
ERROR: [Synth 8-1751] cannot index into non-array cl_sh_pcim_arvalid [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:671]
ERROR: [Synth 8-1751] cannot index into non-array cl_sh_pcim_rready [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:673]
ERROR: [Synth 8-1031] ddr_sh_stat_ack is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:676]
ERROR: [Synth 8-1031] ddr_sh_stat_rdata is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:677]
ERROR: [Synth 8-1031] ddr_sh_stat_rdata is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:678]
ERROR: [Synth 8-1031] ddr_sh_stat_rdata is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:679]
ERROR: [Synth 8-1031] ddr_sh_stat_int is not declared [/home/centos/Composer/Composer-Hardware/vsim/design/composer_aws.sv:680]
"""


def is_number(q):
    # noinspection PyBroadException
    try:
        a = int(q)
    except:
        return False
    return True


def scrape_aws_ports():
    with open(f"{os.environ['COMPOSER_AWS_SDK_DIR']}/hdk/common/shell_stable/design/interfaces/cl_ports.vh") as f:
        inputs = []
        outputs = []
        output_logics = []
        lns = f.readlines()
        stripped = map(lambda x: x.strip().replace(',', '').replace('wire', ''), lns)
        for ln in stripped:
            if '//' in ln:
                ln = ln[ln.find('//')+2:].strip()
            if ln == '':
                continue
            spl = ln.split()
            if spl[0] == 'input':
                ty = 0
            elif spl[0] == 'output':
                if spl[1][:5] == 'logic':
                    ty = 1
                else:
                    ty = 2
            else:
                continue
            # determine width
            if len(spl) < 2:
                continue
            if ln.find('[') != -1:
                # it has a width > 1
                begin = ln.find('[') + 1
                end = ln.find(':')
                width = ln[begin:end].strip()
                subt = ln[ln.rfind(']') + 1:].split()
                name = subt[0]
            else:
                width = 1
                if ty != 1:
                    name = spl[1]
                else:
                    name = spl[2]
            print(f"{ln} => {name}")
            if ty == 0:
                inputs.append((name, width))
            elif ty == 1:
                output_logics.append((name, width))
            else:
                outputs.append((name, width))

    return inputs, outputs, output_logics


def scrape_cl_ports():
    ct = open(f"{os.environ.get('COMPOSER_ROOT')}/Composer-Hardware/vsim/generated-src/composer.v")
    ct_io = []
    wire_id = 0
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
                break
            spl = ln.split()
            if len(spl) == 2:
                # wire is width 1
                width = 1
                name = spl[1]
            else:
                # number before colon, after first character ([)
                width = int(spl[1].split(':')[0][1:]) + 1
                name = spl[2]
            if name.find(',') != -1:
                name = name[:-1]
            name = name.strip()
            if name == 'clock' or name == 'reset':
                continue
            wire_name = f"COMPOSER_wire_{wire_id}"
            wire_id = wire_id + 1
            idx = name.find('bits_')
            if idx != -1:
                dest = name[:idx] + name[idx + 5:]
            else:
                dest = name
            idx = dest.rfind('_')
            dest = (dest[:idx] + dest[idx + 1:]).split('_')[-1]
            ct_io.append({'width': width,
                          'name': name,
                          'wire': wire_name,
                          'setname': dest.split('_')[-1]})
    return ct_io


def scrape_sh_ddr_ports():
    sh_ddr_in = []
    sh_ddr_out = []
    with open(f"{os.environ['COMPOSER_AWS_SDK_DIR']}/hdk/common/shell_stable/design/sh_ddr/sim/sh_ddr.sv") as f:
        lns = f.readlines()
        for ln in lns:
            ln = ln.strip().replace('logic', '')
            if ln.find(');') != -1:
                return sh_ddr_in, sh_ddr_out
            is_input = ln.find('input') != -1
            is_output = ln.find('output') != -1
            if not is_output and not is_input:
                # then it's an inout and not only do we not _want_ to deal with those,
                # but they're already handled (they're the raw DDR pins)
                continue
            bracket_count = ln.count('[')
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

            if bracket_count == 0:
                width = 1
                ar_width = 1
            elif bracket_count == 1:
                width = 1+int(ln[ln.find('[')+1:ln.find(':')])
                ar_width = 1
            elif bracket_count == 2:
                width = 1+int(ln[ln.find('[')+1:ln.find(':')])
                ar_width = 1+int(ln[ln.rfind('[')+1:ln.rfind(':')])
            else:
                print(f"too many bracketk {ln}")
                exit(1)
            if is_input:
                sh_ddr_in.append((name, width, ar_width))
            elif is_output:
                sh_ddr_out.append((name, width, ar_width))
    print("Error: never found ');' in `scrape_sh_ddr_ports()")
    exit(1)


def create_aws_shell():
    # Get io_in and io_out ports for shell so that we can initialize them all to tied off values.
    ports_in, ports_out, ports_logics = scrape_aws_ports()
    to_init = [q[0] for q in ports_out + ports_in]

    cl_io = scrape_cl_ports()
    # Now we have all IOs and their widths, time to organize
    axil_io = list(filter(lambda x: x['name'][:3] == 'ocl', cl_io))
    dram_io = list(filter(lambda x: x['name'][:8] == 'axi4_mem', cl_io))

    # How many AXI4-Mem interfaces did we intialize Composer with?
    if len(dram_io) == 0:
        ndram = 0
    else:
        ndram = max(map(lambda x: int(x['name'].split('_')[2]), dram_io)) + 1

    assert len(axil_io) > 0

    ddr_in, ddr_out = scrape_sh_ddr_ports()

    to_tie = []

    g = open("composer_aws.sv", 'w')
    # Write header
    g.write(f"`include \"composer.v\"\n"
            f"`include \"cl_id_defines.vh\"\n"
            f"`ifndef COMPOSER_DEFINES\n"
            f"`define COMPOSER_DEFINES\n"
            f"`define CL_NAME composer_aws\n"
            f"`define FPGA_LESS_RST\n"
            f"`define NO_XDMA\n")
    # TODO this currently doesn't work for whatever reason, systemverilog doesn't see these defs
    for letter in ['A', 'B', 'D']:
        g.write(f"`ifndef DDR_{letter}_ABSENT\n"
                f"\t`define DDR_{letter}_PRESENT 1\n"
                f"`else\n"
                f"\t`define DDR_{letter}_PRESENT 0\n"
                f"`endif\n")
    g.write("`endif\n")

    # Write module header
    g.write(
        f"module composer_aws #(parameter NUM_PCIE=1, parameter NUM_DDR=4, parameter NUM_HMC=4, parameter NUM_GTY=4)\n"
        f"(\n"
        f"\t`include \"cl_ports.vh\" // fixed ports definition included by build script\n"
        f");\n"
        f"logic pre_sync_rst_n;\n"
        f"logic sync_rst_n;\n"
        f"always_ff @(negedge rst_main_n or posedge clk)\n"
        f"\tif (!rst_main_n)\n"
        f"\tbegin\n"
        f"\t\tpre_sync_rst_n <= 0;\n"
        f"\t\tsync_rst_n <= 0;\n"
        f"\tend\n"
        f"\telse\n"
        f"\tbegin\n"
        f"\t\tpre_sync_rst_n <= 1;\n"
        f"\t\tsync_rst_n <= pre_sync_rst_n;\n"
        f"\tend")
    concats = {}

    ############# INIT ALL COMPOSER STUFF ################
    for pr in cl_io:
        if pr['name'] == 'clock' or pr['name'] == 'reset':
            continue
        if pr['width'] == 1:
            g.write(f"wire {pr['wire']};\n")
        else:
            g.write(f"wire [{int(pr['width']) - 1}:0] {pr['wire']};\n")
    # do tie-offs that can be overriden later
    for port, width in ports_out + ports_logics:
        if port.find('ack') != -1:
            assign = 1
        else:
            assign = 0
        g.write(f"assign {port} = {assign};\n")
    # if len(ports_logics) > 0:
    #     g.write(f"always @(posedge clk)\n"
    #             f"begin\n")
    #     for port, width in ports_logics:
    #         if port.find('ack') != -1:
    #             assign = 1
    #         else:
    #             assign = 0
    #
    #         g.write(f"\t{port} <= {assign};\n")
    #     g.write(f"end\n")

    valid_axi_parts = set()
    # Do AXI4 and OCL concatenations
    for pr in cl_io:
        key = pr['name'].split('_')[0] + '_' + pr['setname']
        if concats.get(key) is None:
            concats[key] = ([pr['wire']], pr['width'])
        else:
            assert concats[key][1] == pr['width']
            concats[key] = (concats[key][0] + [pr['wire']], pr['width'])
    for k in concats.keys():
        lst, width = concats[k]
        if k[:3] == 'ocl':
            if width == 1:
                g.write(f"wire {k};\n")
            else:
                g.write(f"wire [{width - 1}:0] {k};\n")
            g.write(f"assign {k} = {lst[0]};\n")
        elif k[:4] == 'axi4':
            partname = k.split("_")[1]
            valid_axi_parts.add(partname)
            if width == 1:
                g.write(f'wire [2:0] {k};\n')
            else:
                g.write(f'wire [{width - 1}:0] {k} [2:0];\n')
            # first 3 go in the sh_ddr module, last goes directly to shell
            maxidx = min(3, len(lst))
            for i, ele in enumerate(lst[:maxidx]):
                g.write(f"assign {k}[{i}] = {ele};\n")
            for i in range(3 - len(lst) - 1):
                g.write(f"assign {k}[{3 - i}] = {width}'b0;\n")
            found = False
            # deal with DDR_C
            for port_in_name, port_in_width in ports_in:
                if port_in_name.find("ddr_" + partname) != -1:
                    if found:
                        print("FATAL in port_in_name")
                        exit(1)
                    found = True
                    # this non-equal case mostly pertains to ID bits being different
                    if port_in_width != width:
                        if port_in_width > width:
                            print("FATAL port in width headache")
                            exit(1)
                        g.write(f"assign {lst[-1]} = {(port_in_width - width)}'b0, {port_in_name};\n")
                    else:
                        g.write(f"assign {lst[-1]} = {port_in_name};\n")
            if not found:
                for port_out_name, port_out_width in ports_out + ports_logics:
                    if port_out_name.find("ddr_" + partname) != -1:
                        if found:
                            print("FATAL found 2")
                            exit(1)
                        found = True
                        if port_out_width != width:
                            if not is_number(port_out_width) or not is_number(width):
                                print(f"FATAL port2 in width headache '{port_out_name}' '{port_out_width}' '{lst[-1]}' '{width}'")
                                exit(1)
                            g.write(f"assign {port_out_name} = {(int(width) - int(port_out_width))}'b0, {lst[-1]};\n")
                        else:
                            g.write(f"assign {port_out_name} = {lst[-1]};\n")
        else:
            print("GOT A WEIRD KEY: " + str(k))
            exit(1)

    # Route stat pins between sh_ddr module and shell
    ddr_stats = {}
    ddr_wire_id = 0
    # noinspection DuplicatedCode
    for ddr_name, ddr_width, ddr_ar_width in ddr_in:
        if ddr_name.find("stat") == -1:
            continue
        wire_name = f"wire_stat_{ddr_wire_id}"
        ddr_wire_id = ddr_wire_id + 1
        assert ddr_ar_width == 1
        if ddr_width == 1:
            width_str = ''
        else:
            width_str = f'[{ddr_width-1}:0] '
        g.write(f"wire {width_str}{wire_name};\n"
                f"assign {wire_name} = {ddr_name};\n")
        ddr_stats[ddr_name] = wire_name

    # noinspection DuplicatedCode
    for ddr_name, ddr_width, ddr_ar_width in ddr_out:
        if ddr_name.find("stat") == -1:
            continue
        wire_name = f"wire_stat_{ddr_wire_id}"
        ddr_wire_id = ddr_wire_id + 1
        assert ddr_ar_width == 1
        if ddr_width == 1:
            width_str = ''
        else:
            width_str = f'[{ddr_width-1}:0] '
        g.write(f"wire {width_str}{wire_name};\n"
                f"assign {ddr_name} = {wire_name};\n")
        ddr_stats[ddr_name] = wire_name

    # Instantiate actual ComposerTop module
    g.write("ComposerTop myTop(\n"
            "\t.clock(clk),\n"
            "\t.reset(sync_rst_n),\n")
    for i, pr in enumerate(cl_io):
        g.write(f"\t.{pr['name']}({pr['wire']})")
        if i == len(cl_io) - 1:
            g.write("\n")
        else:
            g.write(",\n")
    g.write(');\n')

    # Instantiate SH_DDR module
    g.write(f"// DDR controller instantiation\n"
            f"sh_ddr #(.DDR_A_PRESENT(`DDR_A_PRESENT), .DDR_B_PRESENT(`DDR_B_PRESENT), .DDR_D_PRESENT(`DDR_D_PRESENT))\n"
            f"\tSH_DDR(\n"
            f".clk(clk),\n"
            f".rst_n(sync_rst_n),\n"
            f".stat_clk(clk),\n"
            f".stat_rst_n(sync_rst_n),\n")
    # write signals that go straight to shell (DDR pins)
    for letter, number in [('A', '0'), ('B', '1'), ('D', '3')]:
        g.write(f".CLK_300M_DIMM{number}_DP(CLK_300M_DIMM{number}_DP),\n"
                f".CLK_300M_DIMM{number}_DN(CLK_300M_DIMM{number}_DP),\n"
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
                f".cl_RST_DIMM_{letter}_N(RST_DIMM_{letter}_N)")
    # Now we add connections between AXI4 from composer to the AXI part of the controller
    for name, width, ar_width in ddr_in:
        # special pins, don't worry about these
        if name.find('clk') != -1 or name.find('rst') != -1 or name.find('CLK') != -1 or name.find('RST') != -1\
                or name[:2] == "M_":
            continue
        if name[:10] == "cl_sh_ddr_" or name[:10] == "sh_cl_ddr_":
            if name.find("is_ready") != -1:
                continue
            # Then we're an AXI port
            part = name.split("_")[-1]
            if part in valid_axi_parts:
                g.write(f",\n.{name}(axi4_{part})")
            else:
                # should just be w_id
                to_tie.append((name, width, ar_width))
        elif name.find('stat') != -1:
            g.write(f",\n.{name}({ddr_stats[name]})")
        else:
            print("Found unrecognized port in sh_ddr " + str(name))
            exit(1)

    # don't add ties for unneeded output pins
    for name, width, ar_width in ddr_out:
        # special pins, don't worry about these
        if name.find('clk') != -1 or name.find('rst') != -1 or name.find('CLK') != -1 or name.find('RST') != -1\
                or name[:2] == "M_":
            continue
        if name[:10] == "cl_sh_ddr_" or name[:10] == "sh_cl_ddr_":
            if name.find("is_ready") != -1:
                continue
            # Then we're an AXI port
            part = name.split("_")[-1]
            if part in valid_axi_parts:
                g.write(f",\n.{name}(axi4_{part})")
    g.write(");\n"
            "assign cl_sh_id0 = `CL_SH_ID0;\n"
            "assign cl_sh_id1 = `CL_SH_ID1;\n"
            "assign cl_sh_status1 = `CL_VERSION;\n")

    reserved = ['cl_sh_id0', 'cl_sh_id1', 'cl_sh_status1']

    g.write("// begin tie-offs\n")
    for port_out_name, port_out_width in ports_out + ports_logics:
        lower = str(port_out_name).lower()
        if lower in reserved or port_out_name[:2] == 'M_' or lower.find('ddr') != -1 \
                or lower.find('ocl') != -1 or lower.find('clk') != -1 or lower.find('rst') != -1:
            continue
        if 'ack' in lower:
            set_to = "1"
        else:
            set_to = "0"
        if set_to == '0':
            g.write(f"assign {port_out_name} = {set_to};\n")
        else:
            if int(port_out_width) > 1:
                set_to = f"{port_out_width}'b" + (set_to * int(port_out_width))
            g.write(f"assign {port_out_name} = {set_to};\n")

    g.write("// begin secondary tie-offs\n")
    # Do tie-offs
    for name, width, ar_width in to_tie:
        if 'ack' in name.lower():
            set_to = "1"
        else:
            set_to = "0"
        if width > 1:
            set_to = f"{width}'b" + (set_to * width)
        if ar_width == 1:
            g.write(f"assign {name} = {set_to};\n")
        else:
            for i in range(ar_width):
                g.write(f"assign {name}[{i}] = {set_to};\n")

    g.write("\nendmodule\n")

    g.close()


import os


def is_number(q):
    # noinspection PyBroadException
    try:
        a = int(q)
    except:
        return False
    return True


def scrape_aws_ports():
    with open(f"{os.environ['COMPOSER_ROOT']}/aws-fpga/hdk/common/shell_stable/design/interfaces/cl_ports.vh") as f:
        inputs = []
        outputs = []
        output_logics = []
        lns = f.readlines()
        stripped = map(lambda x: x.strip().replace(',', '').replace('wire', ''), lns)
        for ln in stripped:
            if '//' in ln:
                ln = ln[:ln.find('//')].strip()
            if ln == '':
                continue
            spl = ln.split()
            if 'input' in ln:
                ty = 0
            elif 'output' in ln:
                if 'logic' in ln:
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
                if is_number(width):
                    width = int(width) + 1
            else:
                width = 1
                if ty != 1:
                    name = spl[1]
                else:
                    name = spl[2]
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
                          'direction': spl[0],
                          'setname': dest.split('_')[-1]})
    return ct_io


def scrape_sh_ddr_ports():
    sh_ddr_in = []
    sh_ddr_out = []
    with open(f"{os.environ['COMPOSER_ROOT']}/aws-fpga/hdk/common/shell_stable/design/sh_ddr/sim/sh_ddr.sv") as f:
        lns = f.readlines()
        for ln in lns:
            if '//' in ln:
                ln = ln[:ln.find('//')].strip()
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

            # Find width
            before_name = name_str[:name_start]
            if '[' in before_name:
                width = 1+int(before_name[before_name.find('[')+1:before_name.find(':')])
            else:
                width = 1

            # Find ar_width
            after_name = name_str[name_end:]
            if '[' in after_name:
                ar_width = 1+int(after_name[after_name.find('[')+1:after_name.find(':')])
            else:
                ar_width = 1

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

    def create_wire(nstr, w, arw):
        if w == 1:
            width_str = ""
        else:
            width_str = f'[{w - 1}:0] '
        if arw == 1:
            ar_str = ""
        else:
            ar_str = f" [{arw - 1}:0]"
        g.write(f"wire {width_str}{nstr}{ar_str};\n")

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
            f"`define NO_XDMA\n"
            f"`ifndef CL_VERSION\n"
            f"`define CL_VERSION 32'hee_ee_ee_00\n"
            f"`endif\n")
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
        f"logic clk;\n"
        f"assign clk = clk_main_a0;\n"
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
        f"\tend\n")
    concats = {}

    ############# INIT ALL COMPOSER STUFF ################
    for pr in cl_io:
        if pr['name'] == 'clock' or pr['name'] == 'reset':
            continue
        if pr['width'] == 1:
            g.write(f"wire {pr['wire']};\n")
        else:
            g.write(f"wire [{int(pr['width']) - 1}:0] {pr['wire']};\n")

    valid_axi_parts = set()
    # Do AXI4 and OCL concatenations
    for pr in cl_io:
        key = pr['name'].split('_')[0] + '_' + pr['setname']
        if concats.get(key) is None:
            concats[key] = ([pr['wire']], pr['width'], pr['direction'])
        else:
            assert concats[key][1] == pr['width']
            concats[key] = (concats[key][0] + [pr['wire']], pr['width'], pr['direction'])
    for k in concats.keys():
        lst, width, direction = concats[k]
        partname = k.split("_")[1]
        if k[:3] == 'ocl':
            def search_for_ocl_part(part, part_list):
                for pname, pwidth in part_list:
                    if 'ocl' in pname and "_" + part in pname:
                        print(f"{part} matches in {pname}")
                        return pname, int(pwidth)
                return None, None
            pname, pwidth = search_for_ocl_part(partname, ports_in)
            if pname is not None:
                if pwidth != width:
                    print(f"Warning: CL port '{k}' has width {width} and will be tied to shell port '{pname}' with width '{pwidth}'."
                          f"This may result in unusual behavior due to truncated bits!")
                    g.write(f"assign {lst[0]} = {pname}[{width-1}:0];\n")
                else:
                    g.write(f"assign {lst[0]} = {pname};\n")
            else:
                pname, pwidth = search_for_ocl_part(partname, ports_out + ports_logics)
                if pname is None:
                    if direction == 'input':
                        g.write(f"assign {lst[0]} = 0;\n")
                        print(f"couldn't find match for {partname}/{lst[0]}, tieing to 0")
                    else:
                        print(f"couldn't find match for {partname}")
                    continue
                if pwidth != width:
                    print(f"This happened 3 :( {pname} {partname} {width} {pwidth}")
                g.write(f"assign {pname} = {lst[0]};\n")
        elif k[:4] == 'axi4':
            found = False
            # deal with DDR_C first to scrape out_port width
            is_out = -1
            valid_axi_parts.add(partname)
            def search_for_part(part, part_list):
                for pname, pwidth in part_list:
                    if pname.find("ddr_" + part) != -1:
                        pwidth = int(pwidth)
                        return pname, pwidth
                return None, None
            
            pname, pwidth = search_for_part(partname, ports_in)
            is_out = False
            if pname is not None:
                if pwidth != width:
                    print(f"Warning! CL has part corresponding to {partname} with width{width}. Tieing it to "
                          f"part {pname} with width {pwidth} via truncation which might cause some issues.")
                g.write(f"assign {lst[0]} = {pname};\n")
                is_out = False
            else:
                pname, pwidth = search_for_part(partname, ports_out + ports_logics)
                if pname is None:
                    print(f"Couldn't find {partname} anywhere!")
                    continue
                if pwidth != width:
                    g.write(f"assign {pname} = " + "{" + f"{pwidth-int(width)}'b0, {lst[0]}" + "};\n")
                else:
                    g.write(f"assign {pname} = {lst[0]};\n")
                is_out=True

            def find_ddr_part(part, part_list):
                for dpart, dwidth, darwid in ddr_in + ddr_out:
                    if f"_{part}" in dpart:
                        return dwidth, darwid, dpart
                return None, None

            dwidth, darwid, dpartname = find_ddr_part(partname, ddr_in + ddr_out)
            if dwidth is None:
                dwidth = pwidth
                darwid = 3
            if dwidth == 1:
                dstr = ""
            else:
                dstr = f"[{dwidth-1}:0] "
            if darwid == 1:
                arstr = ""
            else:
                arstr = f" [{darwid-1}:0]"
            g.write(f"wire {dstr}{k}{arstr};\n")
            # first 3 go in the sh_ddr module, last goes directly to shell
            for i, ele in enumerate(lst[1:]):
                if width == pwidth:
                    g.write(f"assign {k}[{i}] = {ele};\n")
                else:
                    g.write(f"assign {k}[{i}] = " + "{" + f"{pwidth-int(width)}'b0, {ele}" + "};\n")
            for i in range(4 - len(lst)):
                g.write(f"assign {k}[{3 - i}] = {pwidth}'b0;\n")

        else:
            print("GOT A WEIRD KEY: " + str(k))
            exit(1)

    # Route stat pins between sh_ddr module and shell
    ddr_stats = {}

    def add_stats_wires(ddr_lst, is_input):
        wire_id = 0
        if is_input:
            wids = 1
        else:
            wids = 0
        if is_input:
            my_list = ddr_in
        else:
            my_list = ddr_out
        for ddr_name, ddr_width, ddr_ar_width in my_list:
            if 'stat' not in ddr_name or 'clk' in ddr_name or 'rst' in ddr_name:
                continue
            wire_name = f"wire_stat_{wids}_{wire_id}"
            wire_id = wire_id + 1
            create_wire(wire_name, ddr_width, ddr_ar_width)
            ddr_stats[ddr_name] = wire_name
            if is_input:
                g.write(f"assign {wire_name} = {ddr_name};\n")
            else:
                g.write(f"assign {ddr_name} = {wire_name};\n")

    add_stats_wires(ddr_in, True)
    add_stats_wires(ddr_out, False)

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
    # CHRIS TODO array is array, even with 1-width wires
    # Instantiate SH_DDR module
    # f"sh_ddr #(.DDR_Ax_PRESENT(`DDR_A_PRESENT), .DDR_B_PRESENT(`DDR_B_PRESENT), .DDR_D_PRESENT(`DDR_D_PRESENT))\n"
    g.write(f"// DDR controller instantiation\n"
            f"sh_ddr #(.DDR_A_PRESENT(1), .DDR_B_PRESENT(1), .DDR_D_PRESENT(1))\n"
            f"\tSH_DDR(\n"
            f".clk(clk),\n"
            f".rst_n(sync_rst_n),\n"
            f".stat_clk(clk),\n"
            f".stat_rst_n(sync_rst_n)")
    # write signals that go straight to shell (DDR pins)
    for letter, number in [('A', '0'), ('B', '1'), ('D', '3')]:
        g.write(f",\n.CLK_300M_DIMM{number}_DP(CLK_300M_DIMM{number}_DP),\n"
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
    for port_out_name, port_width in ports_out + ports_logics:
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
            if int(port_width) > 1:
                set_to = f"{port_width}'b" + (set_to * int(port_width))
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
                "file copy -force $CL_DIR/design/cl_id_defines.vh $TARGET_DIR\n"]
    with open(fname, 'w') as f:
        for ln in lns:
            if "file copy" in ln:
                if to_write is not None:
                    for tw in to_write:
                        f.write(tw)
                    to_write = None
            elif "-lang verilog" in ln:
                f.write("encrypt -k $HDK_SHELL_DIR/build/scripts/vivado_keyfile_2017_4.txt -lang verilog  [glob -nocomplain -- $TARGET_DIR/*.{v,sv,vh,inc}]\n")
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
                g.write(ln[:idx] + "*v" + ln[idx+4:])
            else:
                g.write(ln)


def create_dcp_script_inline(fname):
    os.system(f"sed -i.bu 's/cl_hello_world/composer_aws/g' {fname}")


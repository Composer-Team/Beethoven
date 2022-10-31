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

def scrape_aws_ports():
    with open(f"{os.environ['COMPOSER_AWS_SDK_DIR']}/hdk/common/shell_stable/design/interfaces/cl_ports.vh") as f:
        inputs = []
        outputs = []
        lns = f.readlines()
        stripped = map(lambda x: x.strip().replace('logic', '').replace(',', '').replace('wire', ''), lns)
        for ln in stripped:
            if ln == '':
                continue
            if ln[:2] == '//':
                continue
            spl = ln.split()
            if spl[0] == 'input':
                is_input = True
            elif spl[0] == 'output':
                is_input = False
            else:
                continue
            # determine width
            if len(spl) < 2:
                continue
            if spl[1].find('[') != -1:
                # it has a width > 1
                begin = spl[1].find('[')+1
                end = spl[1].find(':')
                width = spl[1][begin:end]
                name = ln[ln.find(']')+1:].split()[0]
            else:
                width = 1
                name = spl[1]
            if is_input:
                inputs.append((name, width))
            else:
                outputs.append((name, width))
    return inputs, outputs


def create_aws_shell():
    # Get io_in and io_out ports for shell so that we can initialize them all to tied off values.
    ports_in, ports_out = scrape_aws_ports()
    f = open(f"{os.environ.get('COMPOSER_AWS_SDK_DIR')}/hdk/common/shell_stable/new_cl_template/"
             f"design/cl_template.sv")
    ct = open(f"{os.environ.get('COMPOSER_ROOT')}/Composer-Hardware/vsim/generated-src/composer.v")
    # scrape ios from composertop module
    state = 0
    wire_id = 0
    ct_io = []
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
                ct_io.append({'name': name})
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

    # Now we have all IOs and their widths, time to organize
    axil_io = list(filter(lambda x: x['name'][:3] == 'ocl', ct_io))
    dram_io = list(filter(lambda x: x['name'][:8] == 'axi4_mem', ct_io))
    # only remaining pins should be clock and reset
    assert len(dram_io) + len(axil_io) + 2 == len(ct_io)
    # How many AXI4-Mem interfaces did we intialize Composer with?
    if len(dram_io) == 0:
        ndram = 0
    else:
        ndram = max(map(lambda x: int(x['name'].split('_')[2]), dram_io)) + 1
    assert len(axil_io) > 0

    g = open("composer_aws.sv", 'w')
    g.write(f"`include \"composer.v\"\n"
            f"`ifndef COMPOSER_DEFINES\n"
            f"`define COMPOSER_DEFINES\n"
            f"`define CL_NAME composer_aws\n"
            f"`define FPGA_LESS_RST\n"
            f"`define NO_XDMA\n")
    for letter in ['A', 'B', 'D']:
        g.write(f"`ifndef DDR_{letter}_ABSENT\n"
                f"\t`define DDR_{letter}_PRESENT 1\n"
                f"`else\n"
                f"\t`define DDR_{letter}_PRESENT 0\n"
                f"`endif\n")
    g.write("`endif\n")
    flns = f.readlines()
    # copy everything before the sh_ddr module
    state = 0
    sh_ddr_module_pairs = []
    concats = {}

    for ln in flns:
        if state == 0:
            if ln[:18] == 'module cl_template':
                g.write("module composer_aws" + ln[18:])
            else:
                g.write(ln)
            if ln.strip() == ');':
                # init ALL composer stuff
                for pr in ct_io:
                    if pr['name'] != 'clock' and pr['name'] != 'reset':
                        if pr['width'] == 1:
                            g.write(f"wire {pr['wire']};\n")
                        else:
                            g.write(f"wire [{int(pr['width']) - 1}:0] {pr['wire']};\n")
                # do tie-offs that can be overriden later
                for port, width in ports_out:
                    g.write(f"assign {port} = 0;\n")
                for pr in ct_io:
                    if pr['name'] == 'clock' or pr['name'] == 'reset':
                        continue
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
                    else:
                        print("GOT A WEIRD KEY: " + str(k))
                        exit(1)

                g.write("ComposerTop myTop(\n")
                for i, pr in enumerate(ct_io):
                    if pr['name'] == 'clock':
                        g.write(f"\t.clock(clk),\n")
                    elif pr['name'] == 'reset':
                        g.write(f"\t.reset(sync_rst_n),\n")
                    else:
                        g.write(f"\t.{pr['name']}({pr['wire']})")
                        if i == len(ct_io) - 1:
                            g.write("\n")
                        else:
                            g.write(",\n")
                g.write(');\n')
                g.flush()
                # Concatenate signals into coherent names
                state = 1
        elif state == 1:
            g.write(ln)
            if ln.strip()[:6] == 'sh_ddr':
                state = 2
        elif state == 2:
            prefix = ln.strip()
            if len(prefix) < 10:
                if prefix[:2] == ');':
                    state = 3
                if len(prefix) > 0:
                    g.write(ln)
                continue
            sub = ln.strip()[:10]
            if sub == '.sh_cl_ddr' or sub == '.cl_sh_ddr':
                words = ln.split()
                axi_part = words[0][1:].split("_")[3]
                if axi_part == "is" or axi_part == "wid":
                    # wid is only supported in AXI3, we're doing AXI4
                    g.write(ln)
                else:
                    wire = "axi4_" + axi_part
                    g.write(f"\t{words[0]} ({wire}),\n")
                wire_id = wire_id + 1
            else:
                # bug-fix within existing aws code ???
                if prefix.split()[0] == '.ddr_sh_stat_int0':
                    g.write(ln[:-1] + ",\n")
                else:
                    g.write(ln)
        elif state == 3:
            strip = ln.strip()
            if ndram < 4:
                # only need to scrape for DRAM_C if we need all 4 interfaces
                g.write(ln)
                continue
            if len(strip) < 6:
                g.write(ln)
                continue
            if strip[:6] != 'assign':
                g.write(ln)
                continue
            spl = ln.split()
            name = spl[1]
            prefix = name[:9]
            if prefix != 'cl_sh_ddr' and prefix != 'sh_cl_ddr':
                g.write(ln)
                continue
            idx = name.rfind('_')
            part = name[idx + 1:]
            if part == 'wid':
                # wid is only part of AXI3
                g.write(ln)
                continue
            wires, width = concats["axi4_" + part]
            g.write(f"assign {name} = {wires[3]};\n")

    f.close()
    g.close()
    f = "composer_aws.sv"
    # TODO FIX these macros. They should work, but Vivado just doesn't like them...
    os.system(f"sed -i 's/DDR_\\(.\\)_PRESENT(0)/DDR_\\1_PRESENT(1)/g' {f}")

#!/usr/bin/python3

import os

"""
Prepare files for flashing on the FPGA
"""

if os.environ.get('KRIA_IP') is None:
    print("Please define KRIA_IP environment variable")

kria_ip = os.environ['KRIA_IP']

name = input("Provide name of design: ").strip()

os.system("mkdir -p ~/.composer-cache/ && cd ~/.composer-cache/ && git clone -q "
          "https://github.com/Xilinx/device-tree-xlnx.git")

tree_repo = f"{os.environ['HOME']}/.composer-cache/device-tree-xlnx"

with open("dtbo_scripts.tcl", 'w') as f:
    f.write(f"hsi open_hw_design {name}.xsa\nhsi set_repo_path {tree_repo}\nhsi create_sw_design device-tree -os"
            f" device-tree -proc psu_cortexa53_0\nhsi set_property CONFIG.dt_overlay true [hsi::get_os]\n"
            f"hsi generate_target -dir {name}\nhsi close_hw_design {name}")

os.system(f"xsct dtbo_script.tcl && dtc -@ -O dtb -o {name}.dtbo {name}/pl.dtsi")
with open("bootgen.bif", 'w') as f:
    f.write("all:{" + name + ".bit}")

os.system(f"bootgen -w -arch zynqmp -process_bitstream bin -image bootgen.bif && "
          f"ssh petalinux@{kria_ip} mkdir -p designs/{name}/ &&"
          f"scp {name}.bit.bin petalinux@{kria_ip}:~/designs/{name}/ && "
          f"scp {name}.dtbo petalinux@{kria_ip}:~/designs/{name} &&"
          f"scp {os.environ['COMPOSER_ROOT']}/Composer-Hardware/vsim/generated-src/composer_allocator_declaration.h "
          f"petalinux@{kria_ip}:~/designs/{name}")



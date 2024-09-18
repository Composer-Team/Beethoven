#!/usr/bin/python3

import os

opts = list(os.walk(f"{os.environ['HOME']}/designs/"))[0][1]

print("Found the following designs:")
for i, d in enumerate(opts):
    print(f"[{i}] {d}")

choice = int(input("Select which you want to load: "))

chosen_name = opts[choice]
chosen_d = f"{os.environ['HOME']}/designs/{chosen_name}"
lib_d = f"/lib/firmware/xilinx/{chosen_name}"

os.system(f"sudo mkdir -p {lib_d} && sudo cp {chosen_d}/{chosen_name}.dtbo {lib_d}/ && "
          f"sudo cp {chosen_d}/{chosen_name}.bit.bin {lib_d}/ && "
          f"mkdir -p {os.environ['BEETHOVEN_ROOT']}/Beethoven-Hardware/vsim/generated-src/ && "
          f"cp {chosen_d}/beethoven_allocator_declaration.h {os.environ['BEETHOVEN_ROOT']}/Beethoven-Hardware/vsim/generated-src/ && "
          f"sudo cp {os.environ['HOME']}/bin/default_shell.json {lib_d}/shell.json")

os.system(f"sudo dfx-mgr-client -remove && sudo dfx-mgr-client -load {chosen_name}")
os.system(f"cd {os.environ['BEETHOVEN_ROOT']}/Beethoven-Runtime/ && mkdir -p build && "
          f"cd build && cmake .. -DTARGET=fpga -DBACKEND=Kria && make && nohup ./BeethovenRuntime &> runtime.log")

print(f"Runtime should now be running and logging to {os.environ['BEETHOVEN_ROOT']}/Beethoven-Runtime/build/runtime.log")

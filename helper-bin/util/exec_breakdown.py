# Break down an executable into each function and its size in kB

import sys
import os
import subprocess

def get_functions_from_executable(executable):
    # Get the functions from the executable
    obj_dump_out = subprocess.check_output(["objdump", "-t", executable]).decode("utf-8")
    functions = []
    for line in obj_dump_out.split("\n"):
        if not line:
            continue
        parts = line.split()
        try:
            start_addr = int(parts[0], 16)
        except ValueError:
            continue
        name = parts[-1]
        functions.append((start_addr, name))
    functions.sort(key=lambda x: x[0])
    # Get the size of each function
    functions_with_size = []
    for i in range(len(functions) - 1):
        start_addr, name = functions[i]
        next_start_addr = functions[i + 1][0]
        size = next_start_addr - start_addr
        functions_with_size.append((name, size))
    # print the top 20 offending functions
    functions_with_size.sort(key=lambda x: x[1], reverse=True)

# file name to break down is on cmd line first argument
executable = sys.argv[1]
get_functions_from_executable(executable)


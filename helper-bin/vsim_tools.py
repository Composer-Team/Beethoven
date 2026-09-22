import os


def modify_vsim_makefile_in_place(fname):
    with open(fname) as f:
        lns = f.readlines()
    with open(fname, 'w') as f:
        for ln in lns:
            if "C_FILES" in ln:
                find_string = "$(C_TEST_NAME)"
                b = ln.find(find_string)
                assert b != -1
                f.write(ln[:b] + "$(C_SRC_DIR)/vivado_test.c " + ln[b + len(find_string):])
            elif "C_TEST ?=" in ln:
                f.write("export C_TEST ?= vivado_test\n")
            else:
                f.write(ln)

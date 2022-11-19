import os

choice = input("Build sanity for (1) fpga, (2) xsim")
choice = choice.strip()
assert choice in ['1', '2']

file = input("What sanity script to build? (1) alu (2) vector")
file = file.strip()
assert file in ['1', '2']

if choice == '1':
    target = 'sanity_fpga'
else:
    target = 'sanity_xsim'

if file == '1':
    file = 'src/xsim_sanity.cc'
else:
    file = 'src/xsim_vector_sanity.cc'

os.system(f"cmake {os.environ['COMPOSER_ROOT']}/Composer_Verilator -DTARGET={target} -DFILE={file}")


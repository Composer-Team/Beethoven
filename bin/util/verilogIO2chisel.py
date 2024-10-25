import sys


# Given a file `<name>.v` with topmodule <name>, output to text the
# IOs for that module as a Chisel bundle. All multi-bit inputs will
# be UInts, and all single-bit inputs will be Booleans.
def verilog_to_chisel_blackbox(file):
    with open(file, 'r') as f:
        lines = f.readlines()
    # Get the module name
    name = file.split('/')[-1].split('.')[-1]
    # Get the IOs as pairs (name, width)
    inputs = []
    outputs = []
    for ln in lines:
        is_input = ln.find('input') != -1
        is_output = ln.find('output') != -1
        if not is_input and not is_output:
            continue
        width = 1
        if ln.find('[') != -1:
            width = int(ln.split('[')[1].split(':')[0])+1
        wire_name = ln.split()[1].split(';')[0]
        if is_input:
            inputs.append((wire_name, width))
        else:
            outputs.append((wire_name, width))
    # Print the Chisel bundle
    print(f'class {name} extends BlackBox {{')
    print(f'  val io = IO(new Bundle {{')
    for (name, width) in inputs:
        if width == 1:
            print(f'    val {name} = Input(Bool())')
        else:
            print(f'    val {name} = Input(UInt({width}.W))')
    for (name, width) in outputs:
        if width == 1:
            print(f'    val {name} = Output(Bool())')
        else:
            print(f'    val {name} = Output(UInt({width}.W))')
    print(f'  }})')
    print(f'}}')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: verilogIO2chisel.py <file.v>')
        sys.exit(1)
    verilog_to_chisel_blackbox(sys.argv[1])
    sys.exit(0)


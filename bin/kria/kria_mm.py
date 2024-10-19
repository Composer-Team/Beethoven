import os
import sys

# First, check that we're running in sudo
if os.geteuid() != 0:
    print("This script must be run as root")
    sys.exit(1)

# look in /sys/kernel/mm/hugepages for the number of hugepages
hugepage_dirs = list(os.walk('/sys/kernel/mm/hugepages'))[0][1]
longest_string = max([len(directory) for directory in hugepage_dirs])

print("Hugepage allocations----------------------\n"
      f"[idx]\t[name]{' ' * (max(longest_string - 6, 0))}\t[n_alloc]\t[n_free]\n")
for i, directory in enumerate(hugepage_dirs):
    with open(f"/sys/kernel/mm/hugepages/{directory}/nr_hugepages", 'r') as f:
        n_alloc = f.read().strip()
    with open(f"/sys/kernel/mm/hugepages/{directory}/free_hugepages", 'r') as f:
        n_free = f.read().strip()
    padded_directory = directory + " " * (longest_string - len(directory))
    print(f"[{i}]\t{padded_directory}\t{n_alloc}\t\t{n_free}")
print("Which hugepage allocation to modify (enter to quit)")
idx = input("> ").strip()
if not idx:
    sys.exit(0)
else:
    idx = int(idx)

directory = hugepage_dirs[idx]
current_alloc = int(open(f"/sys/kernel/mm/hugepages/{directory}/nr_hugepages", 'r').read().strip())
current_free = int(open(f"/sys/kernel/mm/hugepages/{directory}/free_hugepages", 'r').read().strip())

print(f"Current allocation of [{directory}]: {current_free}/{current_alloc} available")
set_to = int(input("How many hugepages to set the max allocation to?\n> ").strip())

diff = set_to - current_alloc
if diff < 0 and abs(diff) > current_free:
    print(f"Error: Not enough free hugepages to deallocate {abs(diff)}")
    sys.exit(1)

with open(f"/sys/kernel/mm/hugepages/{directory}/nr_hugepages", 'w') as f:
    f.write(str(set_to))
print(f"Set allocation of [{directory}] to {set_to}. Waiting a second to recheck...")
os.system("sleep 1")
print(f"Rechecking...")
current_alloc = int(open(f"/sys/kernel/mm/hugepages/{directory}/nr_hugepages", 'r').read().strip())
if current_alloc != set_to:
    print(f"Error: Failed to set allocation of [{directory}] to {set_to}")
    sys.exit(1)
print(f"Successfully set allocation of [{directory}] to {set_to}")
sys.exit(0)





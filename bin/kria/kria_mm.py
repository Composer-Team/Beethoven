import os
import sys

# First, check that we're running in sudo
if os.geteuid() != 0:
    print("This script must be run as root")
    sys.exit(1)

# look in /sys/kernel/mm/hugepages for the number of hugepages
hugepage_dirs = list(os.walk('/sys/kernel/mm/hugepages'))[0][1]

print("Hugepage allocations----------------------\n"
      "[id]\t[name]\t[n_alloc]\t[n_free]\n")
for dir, i in enumerate(hugepage_dirs):
    with open(f"/sys/kernel/mm/hugepages/{dir}/nr_hugepages", 'r') as f:
        n_alloc = f.read().strip()
    with open(f"/sys/kernel/mm/hugepages/{dir}/free_hugepages", 'r') as f:
        n_free = f.read().strip()
    print(f"[{i}]\t{dir}\t{n_alloc}\t{n_free}")

print("Which hugepage allocation to modify")
id = int(input("> ").strip())

current_alloc = int(open(f"/sys/kernel/mm/hugepages/{id}/nr_hugepages", 'r').read().strip())
current_free = int(open(f"/sys/kernel/mm/hugepages/{id}/free_hugepages", 'r').read().strip())

print(f"Current allocation of [{id}]: {current_free}/{current_alloc} available")
set_to = int(input("How many hugepages to set the max allocation to?\n> ").strip())

diff = set_to - current_alloc
if diff < 0 and abs(diff) > current_free:
    print(f"Error: Not enough free hugepages to deallocate {abs(diff)}")
    sys.exit(1)

with open(f"/sys/kernel/mm/hugepages/{id}/nr_hugepages", 'w') as f:
    f.write(str(set_to))
print(f"Set allocation of [{id}] to {set_to}. Waiting a second to recheck...")
os.system("sleep 1")
print(f"Rechecking...")
current_alloc = int(open(f"/sys/kernel/mm/hugepages/{id}/nr_hugepages", 'r').read().strip())
if current_alloc != set_to:
    print(f"Error: Failed to set allocation of [{id}] to {set_to}")
    sys.exit(1)
print(f"Successfully set allocation of [{id}] to {set_to}")
sys.exit(0)





//
// Created by Chris Kjellqvist on 10/13/22.
//

#include <composer/fpga_handle_sim.h>
#include <iostream>
#include <composer_allocator_declaration.h>

using namespace composer;
using dtype=uint16_t;
int main() {
  fpga_handle_sim_t fpga;
  int n_numbers = 1024;
  // allocate space on the fpga
  auto fpga_read = fpga.malloc(sizeof(dtype) * n_numbers);
  auto fpga_write = fpga.malloc(sizeof(dtype) * n_numbers);
  auto my_array = new dtype[n_numbers];
  for (int i = 0; i < n_numbers; ++i) {
    my_array[i] = i;
  }
  // copy data to fpga
  fpga.copy_to_fpga(fpga_read, my_array);
  printf("Sending addresses %16llx and %16llx to fpga\n", fpga_read.getFpgaAddr(), fpga_write.getFpgaAddr());

  // this interface could use some work...
  // though some notable improvements: attempting to wait for these commands will issue an error
  rocc_cmd::addr_cmd(VectorSystem_ID, 0, 0, channel::read, fpga_read).send();
  rocc_cmd::addr_cmd(VectorSystem_ID, 0, 0, channel::write, fpga_write).send();

  // send command and wait for response
  rocc_cmd::start_cmd(VectorSystem_ID, 0, 0, true,
                      composer::RD::R0, 0, 0, 0, n_numbers, 15).send().get();

  // check result
  fpga.copy_from_fpga(my_array, fpga_write);
  for (int i = 0; i < n_numbers; ++i) {
    printf("Was: %d\tExpect: %d\tGot: %d\n", i, i+15, my_array[i]);
  }
}
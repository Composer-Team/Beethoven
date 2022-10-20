//
// Created by Chris Kjellqvist on 10/13/22.
//

#include <composer/fpga_handle_sim.h>
#include <composer_allocator_declaration.h>
using namespace composer;

int main() {
  fpga_handle_sim_t vsim;
  // test add 32 + 64 = 96
  auto add_res = rocc_cmd::start_cmd(ALUSystem_ID,0,0,true,
                                     RD::R0, 0, 0, 0, 32, 64).send().get();

  if (add_res.data != 96) {
    printf("Did not receive expected response (96), got %llu instead!\n", add_res.data);
    exit(1);
  } else {
    printf("Passed add\n");
  }
  // test subs
  auto sub_resp = rocc_cmd::start_cmd(ALUSystem_ID,1,0,true,
                                      RD::R0, 0, 0, 0, 135, 35).send().get();
  if (sub_resp.data != 100) {
    printf("Did not receive expected response (100), got %llu instead!\n", sub_resp.data);
    exit(1);
  } else {
    printf("Passed sub\n");
  }

  // test mult
  auto mult_resp = rocc_cmd::start_cmd(ALUSystem_ID, 2, 0,
                                       true, RD::R0, 0, 0, 0,
                                       7, 9).send().get();
  if (mult_resp.data != 63) {
    printf("Did not receive expected response (100), got %llu instead!\n", mult_resp.data);
    exit(1);
  } else {
    printf("Passed mult\n");
  }
}
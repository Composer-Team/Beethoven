---
id: aws-f2
title: AWS F2 Platform
sidebar_label: AWS F2
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# AWS F2 FPGA Platform

AWS F2 instances provide access to Xilinx Virtex UltraScale+ VU9P FPGAs with 3 dies (SLRs), 16GB DDR4 memory, and high-bandwidth PCIe connectivity. Beethoven supports the complete F2 development workflow from simulation to cloud deployment.

<Tabs>
<TabItem value="overview" label="Overview & Prerequisites" default>

## Overview

The AWS F2 development workflow uses a two-instance approach:
- **Build Instance**: EC2 instance with Vivado for running synthesis and place-and-route
- **F2 Instance**: f2.2xlarge with actual FPGA for deployment and testing

## Prerequisites

### AWS Account Setup

1. **AWS CLI Configuration**
```bash
aws configure
# Enter your AWS access key ID, secret key, and default region
```

2. **S3 Bucket for Artifacts**
```bash
aws s3 mb s3://beethoven-<your-username>
```

3. **EC2 Key Pair**
Create or import an SSH key pair in your AWS region for instance access.

### Required Tools (Local Machine)

- **Scala/sbt**: For Beethoven hardware generation
- **AWS CLI**: For managing instances and AFI creation
- **SSH**: For connecting to build and F2 instances

### F2 Instance Access

Request F2 instance access through AWS support if not already enabled for your account.

## Workflow Summary

The complete F2 development workflow consists of 6 steps:

1. **Verify Architecture in Simulation** - Test with `BuildMode.Simulation`
2. **Initialize F2 Build Instance** - Run `aws-init` script for one-time setup
3. **Generate with Synthesis Mode** - Use `BuildMode.Synthesis` (auto-copies to build instance)
4. **Run Build on Instance** - Execute `aws_build_dcp_from_cl.py` for synthesis and P&R
5. **Transfer DCP** - Use `aws-build-mv` to move design checkpoint to S3
6. **Deploy to F2** - Create AFI and load onto F2 instance

</TabItem>

<TabItem value="step1" label="Step 1: Verify in Simulation">

## Step 1: Verify Architecture in Simulation

Before attempting F2 synthesis, you **must** verify your design works correctly in simulation. F2 builds take hours, so catching issues early saves time and cost.

### Configure for Simulation

```scala title="Build configuration with simulation mode"
import beethoven._
import beethoven.Platforms._

object MyAcceleratorBuild extends BeethovenBuild(
  config = new MyAcceleratorConfig,
  platform = new AWSF2Platform,
  buildMode = BuildMode.Simulation  // Start with simulation
)
```

### Generate and Test

```bash title="Generate hardware for simulation"
cd Beethoven-Hardware
export BEETHOVEN_PATH=`pwd`/../my-beethoven-output
sbt run
# Select MyAcceleratorBuild from the menu
```

### Run Simulation Tests

```bash title="Build and run simulation"
cd Beethoven-Runtime
mkdir build && cd build
cmake .. -DTARGET=sim -DSIMULATOR=verilator
make -j

# Run your testbench
cd ../../testbench
mkdir build && cd build
cmake ..
make
./my_testbench
```

:::tip Debugging in Simulation
Use waveform viewers (GTKWave for Verilator, DVE for VCS) to debug issues before moving to F2. See the [Debugging Guide](/docs/hardware/debugging) for details.
:::

### Verify Functionality

Ensure all tests pass and results match expected behavior. Only proceed to Step 2 once you're confident the design is correct.

</TabItem>

<TabItem value="step2" label="Step 2: Initialize Build Instance">

## Step 2: Initialize F2 Build Instance

The build instance runs Vivado synthesis and place-and-route. This is a one-time setup per build instance.

### Launch Build Instance

Launch an EC2 instance with the FPGA Developer AMI (has Vivado pre-installed):

```bash title="Launch build instance"
aws ec2 run-instances \
  --image-id <FPGA_Developer_AMI_ID> \
  --instance-type c5.4xlarge \
  --key-name <your-key-pair> \
  --security-group-ids <your-sg> \
  --subnet-id <your-subnet>
```

:::note Instance Type Recommendation
Use an instance with the **fastest clock rate** for quicker builds. Compute-optimized instances (c5 family) are recommended. The build instance does not need an FPGA attached.
:::

### Run Initial Setup Script

SSH into the build instance and run the `aws-init` script:

```bash title="Initialize build environment"
ssh ubuntu@<BUILD_INSTANCE_IP>

# Transfer and run aws-init script
# (Script should be provided in Beethoven-Software/bin/)
./aws-init

# This script:
# 1. Clones aws-fpga repository to ~/aws-fpga
# 2. Sets up environment variables
# 3. Copies Beethoven build scripts to instance
# 4. Adds Beethoven scripts to your PATH (including aws-build-mv)
```

The `aws-init` script prepares your build instance for the Beethoven workflow. After running it, Beethoven-specific commands like `aws-build-mv` will be available in your shell.

### Verify Setup

Ensure the aws-fpga repository is cloned:

```bash
ls ~/aws-fpga
# Should show: hdk/ sdk/ Vitis/ ...
```

Keep this instance running for the next steps.

</TabItem>

<TabItem value="step3" label="Step 3: Synthesis Mode Generation">

## Step 3: Generate with BuildMode.Synthesis

After verifying in simulation, switch to synthesis mode. This generates production RTL and automatically copies files to your build instance.

### Configure for Synthesis

```scala title="Build configuration with synthesis mode"
import beethoven._
import beethoven.Platforms._

object MyAcceleratorBuild extends BeethovenBuild(
  config = new MyAcceleratorConfig,
  platform = new AWSF2Platform,
  buildMode = BuildMode.Synthesis  // Switch to synthesis mode
)
```

### Generate Hardware

:::warning Build Instance Must Be Running
Ensure your F2 build instance is running before this step. BuildMode.Synthesis triggers post-generation steps that copy your design files to the build instance automatically.
:::

```bash title="Generate hardware for synthesis"
cd Beethoven-Hardware
export BEETHOVEN_PATH=`pwd`/../my-beethoven-output
sbt run
# Select MyAcceleratorBuild from the menu
```

**What happens during synthesis mode generation:**
1. Verilog RTL is generated to `$BEETHOVEN_PATH/build/hw/`
2. C++ bindings are generated to `$BEETHOVEN_PATH/build/beethoven_hardware.{h,cc}`
3. **Post-generation copies design files to build instance** at `~/cl_beethoven_top/`

This automatic transfer replaces the legacy manual workflow.

### Verify Files on Build Instance

SSH to your build instance and check:

```bash
ssh ubuntu@<BUILD_INSTANCE_IP>
ls ~/cl_beethoven_top/design/
# Should show your generated Verilog files
```

</TabItem>

<TabItem value="step4" label="Step 4: Run Build on Instance">

## Step 4: Run Build on F2 Instance

On the build instance, run Vivado synthesis and place-and-route using the AWS-provided build script.

### Source HDK Setup

```bash title="Set up Vivado environment"
ssh ubuntu@<BUILD_INSTANCE_IP>
cd ~/aws-fpga
source hdk_setup.sh
```

### Navigate to Build Directory

```bash
cd ~/cl_beethoven_top/build/scripts/
```

### Run Build Script

```bash title="Run synthesis and place-and-route"
python3 ./aws_build_dcp_from_cl.py --cl cl_beethoven_top
```

:::note Build Script Options
The `--cl` flag is **required** and specifies the custom logic name. Additional options are available; consult the aws-fpga repository documentation for advanced configuration.
:::

### Monitor Build Progress

The build process takes **2-4 hours** depending on design complexity and instance type. Monitor progress:

```bash
# Build logs are written to:
tail -f ~/cl_beethoven_top/build/scripts/last_log/
```

### Check Timing Results

At the **end** of the build script execution, timing results are reported. Look for:

```
Post-Route Timing Summary:
  WNS (Worst Negative Slack): 0.123 ns
  TNS (Total Negative Slack): 0.000 ns
  WHS (Worst Hold Slack): 0.089 ns
```

:::danger Timing Failures
If WNS is negative, your design has setup timing violations and **will not function correctly**. You must address timing issues before proceeding. See [Troubleshooting](#timing-violations) for solutions.
:::

### Locate Generated DCP

After a successful build, the design checkpoint (DCP) is located at:

```
~/cl_beethoven_top/build/checkpoints/to_aws/
```

</TabItem>

<TabItem value="step5" label="Step 5: Transfer DCP">

## Step 5: Transfer DCP with aws-build-mv

After a successful build with no timing failures, use the `aws-build-mv` script to transfer the design checkpoint to S3 and prepare for AFI creation.

### Run Transfer Script

```bash title="Move DCP to S3"
ssh ubuntu@<BUILD_INSTANCE_IP>
aws-build-mv
```

This script is available in your PATH because `aws-init` configured it during Step 2.

### Follow Prompts

The script will:
1. **Verify DCP exists** at `~/cl_beethoven_top/build/checkpoints/to_aws/`
2. **Prompt for S3 bucket** (e.g., `s3://beethoven-<username>`)
3. **Upload DCP to S3** for AFI creation
4. **Copy DCP to F2 instance** (if specified)

Example interaction:

```
DCP found: SH_CL_routed.dcp
Enter S3 bucket for upload: s3://beethoven-myusername
Uploading to S3... Done.
Copy to F2 instance? (y/n): y
Enter F2 instance IP: 18.xxx.xxx.xxx
Copying... Done.
```

### Verify S3 Upload

```bash
aws s3 ls s3://beethoven-<username>/
# Should show your DCP file
```

The DCP is now ready for AFI creation.

</TabItem>

<TabItem value="step6" label="Step 6: Deploy to F2">

## Step 6: Create AFI and Deploy

Use the DCP in S3 to create an Amazon FPGA Image (AFI), then load it onto your F2 instance.

### Launch F2 Instance

```bash title="Launch F2 instance"
aws ec2 run-instances \
  --image-id <FPGA_Developer_AMI_ID> \
  --instance-type f2.2xlarge \
  --key-name <your-key-pair> \
  --security-group-ids <your-sg> \
  --subnet-id <your-subnet>
```

### Create AFI

```bash title="Create FPGA image from DCP"
aws ec2 create-fpga-image \
  --name "my-beethoven-accel" \
  --description "Beethoven accelerator" \
  --input-storage-location Bucket=beethoven-<username>,Key=SH_CL_routed.dcp \
  --logs-storage-location Bucket=beethoven-<username>,Key=logs/
```

This returns an AFI ID (e.g., `afi-0123456789abcdef0`).

### Check AFI Status

AFI creation takes **30-60 minutes**. Monitor status:

```bash title="Check AFI status"
aws ec2 describe-fpga-images --fpga-image-ids afi-0123456789abcdef0
```

Wait until `State` shows `available`.

### Load AFI onto F2 Instance

SSH to your F2 instance:

```bash
ssh ubuntu@<F2_INSTANCE_IP>

# Load FPGA drivers
sudo fpga-load-local-image -S 0 -I afi-0123456789abcdef0

# Verify loaded
sudo fpga-describe-local-image -S 0 -H
# Should show "loaded" status
```

### Build and Run Runtime

```bash title="Build Beethoven Runtime for F2"
cd Beethoven-Runtime
mkdir build && cd build
cmake .. -DTARGET=fpga -DBACKEND=AWS_F2
make -j
sudo ./BeethovenRuntime
```

### Run Your Testbench

```bash title="Compile and run testbench"
cd testbench
mkdir build && cd build
cmake ..
make
sudo ./my_testbench
```

:::note Sudo Required
FPGA access requires root privileges. Always run with `sudo`.
:::

Your accelerator is now running on AWS F2 hardware.

</TabItem>

<TabItem value="troubleshooting" label="Troubleshooting & Reference">

## Troubleshooting

### Timing Violations

**Symptoms:** WNS (Worst Negative Slack) is negative after build

**Solutions:**
1. **Reduce Clock Frequency**: Lower `clockRateMHz` in `AWSF2Platform` configuration
2. **Add Pipeline Stages**: Use `RegNext()` on critical paths
3. **Improve Floorplanning**: Place related modules on the same SLR using `DeviceContext.withDevice()`
4. **Review Critical Path**: Check Vivado timing reports to identify bottlenecks

See [Floorplanning Guide](/docs/hardware/floorplanning) for multi-die optimization strategies.

---

### Build Instance Connection Issues

**Symptoms:** Cannot SSH to build instance, or `aws-init` script not found

**Solutions:**
1. Verify security group allows SSH (port 22) from your IP
2. Check instance state: `aws ec2 describe-instances --instance-ids <id>`
3. Ensure you're using the correct key pair
4. Verify `aws-init` script was transferred to the instance

---

### Post-Generation Copy Fails

**Symptoms:** Files not appearing at `~/cl_beethoven_top/` on build instance

**Solutions:**
1. Verify build instance is running before `sbt run`
2. Check network connectivity between local machine and build instance
3. Review post-generation logs for errors
4. Ensure SSH keys are configured correctly

---

### AFI Creation Fails

**Symptoms:** `create-fpga-image` returns error, or AFI status shows `failed`

**Solutions:**
1. Check S3 bucket permissions (must be readable by AWS FPGA service)
2. Verify DCP was uploaded successfully: `aws s3 ls s3://bucket-name/`
3. Review AFI creation logs in S3 logs folder
4. Ensure DCP was generated from a build with no timing violations

---

### F2 Instance Can't Load AFI

**Symptoms:** `fpga-load-local-image` fails or shows "not loaded"

**Solutions:**
1. Verify AFI is in `available` state before loading
2. Check FPGA slot status: `sudo fpga-describe-local-image -S 0`
3. Clear any existing images: `sudo fpga-clear-local-image -S 0`
4. Reload drivers: `sudo rmmod edma && sudo modprobe edma`

---

## Reference

### AWS F2 Platform Specifications

| Component | Specification |
|-----------|---------------|
| **FPGA** | Xilinx Virtex UltraScale+ VU9P |
| **Dies (SLRs)** | 3 (SLR0, SLR1, SLR2) |
| **Memory** | 16GB DDR4 (discrete) |
| **Memory Channels** | 1 (512-bit AXI4) |
| **Clock Rate** | 250 MHz (default) |
| **Interface** | PCIe Gen3 x16 |
| **Memory Bandwidth** | 250 MHz × 64 bytes = 16 GB/s |

### Platform Configuration

```scala title="AWSF2Platform definition"
class AWSF2Platform(implicit p: Parameters) extends Platform {
  override val platformType = FPGA
  override val hasDiscreteMemory = true
  override val physicalMemoryBytes = 16L * 1024 * 1024 * 1024
  override val memoryNChannels = 1
  override val memoryControllerBeatBytes = 64  // 512-bit
  override val clockRateMHz = 250

  // Multi-die topology
  override val physicalDevices = List(
    DeviceConfig(0, "pblock_SLR0"),
    DeviceConfig(1, "pblock_SLR1"),
    DeviceConfig(2, "pblock_SLR2")
  )
  override val physicalConnectivity = List((0,1), (1,2))
}
```

### Script Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `aws-init` | One-time build instance setup | Step 2 (first-time setup) |
| `aws_build_dcp_from_cl.py` | Run Vivado synthesis and P&R | Step 4 (on build instance) |
| `aws-build-mv` | Transfer DCP to S3 and F2 | Step 5 (after successful build) |

### Key Workflow Differences from Other Platforms

| Feature | AWS F2 | Kria | U200 |
|---------|--------|------|------|
| **Memory** | Discrete (DMA required) | Shared (PS-PL) | Discrete (DMA required) |
| **Build Flow** | Cloud-based (AFI) | On-premises (bitstream) | On-premises (bitstream) |
| **Deployment** | Load AFI via AWS CLI | Load via Vivado or JTAG | Load via Vivado Hardware Manager |
| **Shell** | AWS F2 Shell (pre-built) | Custom Zynq integration | Custom shell required |
| **Synthesis** | Remote (build instance) | Local or remote | Local or remote |

### See Also

- [Floorplanning Guide](/docs/hardware/floorplanning) - Multi-die SLR optimization
- [Debugging Guide](/docs/hardware/debugging) - Troubleshooting techniques
- [Memory Interfaces](/docs/hardware/memory) - Memory channel configuration
- [U200 Platform](/docs/platforms/u200) - Similar 3-die platform (on-premises)

</TabItem>
</Tabs>

# AWS F2 Implementation Flow

## Why AWS F2?

AWS F2 instances provide on-demand access to Xilinx Virtex UltraScale+ FPGAs without upfront hardware costs. This is valuable for:
- **Rapid prototyping**: Test accelerator designs before committing to custom silicon
- **Scalable deployment**: Spin up multiple FPGA instances for parallel workloads
- **No hardware management**: AWS handles power, cooling, and PCIe connectivity

The tradeoff is a more complex build flow: you generate hardware locally, transfer it to an F2 instance, run Vivado synthesis there, then create an Amazon FPGA Image (AFI) that can be loaded on any F2 instance.

## Prerequisites

1. **AWS Account** with EC2 and S3 permissions
2. **F2 Instance Access** - You need an F2 instance for building (the synthesis server doesn't need an FPGA, but the development AMI has Vivado pre-installed)
3. **AWS CLI** configured with credentials
4. **Local Environment** with Beethoven installed

## Build Flow Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Local Machine  │────▶│  F2 Build Host  │────▶│   AWS S3/AFI    │
│  (sbt run)      │     │  (Vivado synth) │     │  (deployment)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. **Local**: Generate RTL from Scala configuration
2. **F2 Instance**: Run Vivado synthesis and place-and-route
3. **AWS**: Create AFI from design checkpoint, deploy to any F2

## Step 1: Configure Your Platform

In your Scala build configuration, use `AWSF2Platform`:

```scala
object MyAcceleratorBuild extends BeethovenBuild(
  platform = AWSF2Platform,
  config = new MyAcceleratorConfig
)
```

### F2 Platform Characteristics

| Property | Value |
|----------|-------|
| Memory | Single DDR4 channel, 16GB |
| Clock | 250 MHz (configurable via clock recipes) |
| Interface | AXI4 front bus (32-bit), AXI DMA (512-bit) |
| FPGA | 3 SLRs with BRAM/URAM resources |

The platform automatically configures:
- Memory address space (0x400000000 bytes)
- AXI interface widths
- Shell integration for DDR, DMA, and control interfaces

## Step 2: Generate Hardware

Run sbt to generate RTL and build scripts:

```bash
cd Beethoven-Hardware
sbt run
```

This produces:
```
<build>/aws/
├── cl_beethoven_top/
│   ├── design/           # Generated Verilog
│   │   ├── BeethovenTop.sv
│   │   ├── cl_beethoven_top.sv
│   │   └── [accelerator modules]
│   └── build/
│       ├── scripts/      # Vivado TCL scripts
│       └── constraints/  # Timing/placement XDC files
```

## Step 3: Set Up F2 Build Instance

### First-Time Setup

Run the initialization script to configure your F2 instance:

```bash
cd Composer/bin
./aws-init
```

You'll be prompted for the EC2 instance IP. The script:
1. Copies Beethoven tools to the instance
2. Clones the aws-fpga repository
3. Sets up environment variables

### Transfer and Build

Use `aws-gen-build` to transfer your design to the F2 instance:

```bash
./aws-gen-build
```

When prompted, enter the F2 instance IP address. The script:
1. Transfers generated sources via rsync
2. Sets up the build directory structure
3. Copies AWS HDK build scripts

## Step 4: Run Vivado Synthesis

SSH to your F2 instance and run the build:

```bash
ssh ubuntu@<F2_IP>
cd ~/cl_beethoven_top/build/scripts
source ~/aws-fpga/hdk_setup.sh

# Run synthesis and place-and-route
./aws_build_dcp_from_cl.sh -strategy DEFAULT
```

### Build Options

| Option | Values | Purpose |
|--------|--------|---------|
| `-strategy` | DEFAULT, TIMING, EXPLORE | Vivado optimization strategy |
| `-clock_recipe_a` | A0, A1, A2 | Clock group A frequency |
| `-uram_option` | 2, 3, 4 | URAM utilization (50%, 75%, 100%) |
| `-foreground` | flag | Run in foreground (shows progress) |

The build takes 2-4 hours depending on design complexity. Output:
```
~/cl_beethoven_top/build/
├── checkpoints/
│   └── <timestamp>.Developer_CL.tar  # Design checkpoint
└── reports/
    └── <timestamp>.post_route_timing.rpt
```

## Step 5: Create AFI

After synthesis completes successfully, use `aws-build-mv` to create the AFI:

```bash
./aws-build-mv
```

The script:
1. **Validates timing**: Checks for setup/hold violations
2. **Creates S3 bucket**: `beethoven-<username>` for storing artifacts
3. **Uploads DCP**: Transfers design checkpoint to S3
4. **Submits AFI creation**: Calls `aws ec2 create-fpga-image`

### Monitor AFI Status

AFI creation takes 30-60 minutes. Check status:

```bash
aws ec2 describe-fpga-images --owner self
```

States: `pending` → `available` (success) or `failed`

## Step 6: Deploy

Once the AFI is available, you can load it on any F2 instance:

```bash
# Clear any existing FPGA image
sudo fpga-clear-local-image -S 0

# Load your AFI
sudo fpga-load-local-image -S 0 -I <afi-id>

# Verify
fpga-describe-local-image -S 0 -H
```

## Troubleshooting

### Timing Violations

If `aws-build-mv` reports timing violations:
1. Check `<timestamp>.post_route_timing.rpt` for failing paths
2. Try `-strategy TIMING` for more aggressive optimization
3. Reduce clock frequency via clock recipes
4. Simplify critical paths in your accelerator

### AFI Creation Fails

Check the AFI logs in S3:
```bash
aws s3 ls s3://beethoven-<username>/logs/
aws s3 cp s3://beethoven-<username>/logs/<afi-id>/ ./logs/ --recursive
```

Common issues:
- Design too large for shell constraints
- Clock crossing violations
- Memory interface issues

## F1 vs F2 Differences

| Aspect | F1 | F2 |
|--------|----|----|
| User | ec2-user | ubuntu |
| Build dir | ~/build-dir/ | ~/cl_beethoven_top/ |
| Memory channels | Configurable | Single channel |

If targeting F1 instead, use `AWSF1Platform`.

## Related Documentation

- [New Platform Guide](/Beethoven/Platform/NewPlatform) - Creating custom platforms
- [Kria Platform](/Beethoven/Platform/Kria) - Alternative FPGA target
- [AWS FPGA Developer Guide](https://github.com/aws/aws-fpga) - AWS HDK documentation

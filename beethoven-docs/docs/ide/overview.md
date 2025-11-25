---
id: overview
title: IDE Integration
sidebar_label: IDE Setup
---

# IDE Setup

Beethoven development spans two languages: Scala/Chisel for hardware and C++ for testbenches. This guide covers setting up IDEs for productive development in both.

## VSCode with Beethoven Extension (Recommended)

The Beethoven VSCode extension bridges the gap between Scala and C++ development, providing cross-language features that generic setups lack.

### Why Use the Beethoven Extension?

When you modify an `AccelCommand` in Scala, the generated C++ header changes. Without tooling support, you'd need to:
1. Manually run sbt to regenerate headers
2. Restart clangd to pick up changes
3. Remember which Scala class corresponds to which C++ function

The extension automates this: edit Scala, save, and C++ immediately sees the new interface with working autocompletion and go-to-definition back to Scala sources.

### Installation

Install the Beethoven extension from the VSCode Marketplace:

1. Open VSCode Extensions (Cmd+Shift+X / Ctrl+Shift+X)
2. Search for "Beethoven"
3. Click Install on the Beethoven extension

Or install directly from the [VSCode Marketplace](https://marketplace.visualstudio.com/items?itemName=composer-team.beethoven).

### Required Extensions

Install these companions for full functionality:

| Extension | Purpose |
|-----------|---------|
| **Metals** (scalameta.metals) | Scala language server |
| **clangd** (llvm-vs-code-extensions.vscode-clangd) | C++ language server |

### Configuration

Open Settings (JSON) and configure:

```json
{
  "beethoven.hardwarePath": "/path/to/Beethoven-Hardware",
  "beethoven.outputPath": "${workspaceFolder}/build",
  "beethoven.mainClass": "com.example.MyAcceleratorBuild",
  "beethoven.autoRegenerate": true
}
```

| Setting | Description |
|---------|-------------|
| `hardwarePath` | Path to Beethoven-Hardware (auto-detected if in workspace) |
| `outputPath` | Where `beethoven_hardware.h` is generated |
| `mainClass` | Your Scala main class for hardware generation |
| `autoRegenerate` | Regenerate headers automatically on Scala save |

### Workflow

```
┌─────────────────┐
│  Edit Scala     │
│  AccelCommand   │
└────────┬────────┘
         │ save
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Metals/Bloop   │────▶│  Beethoven ext  │
│  compiles       │     │  detects change │
└─────────────────┘     └────────┬────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
┌─────────────────┐                             ┌─────────────────┐
│  Regenerate     │                             │  Update clangd  │
│  C++ headers    │                             │  include paths  │
└────────┬────────┘                             └────────┬────────┘
         │                                               │
         └───────────────────────┬───────────────────────┘
                                 ▼
                        ┌─────────────────┐
                        │  C++ code gets  │
                        │  completions &  │
                        │  go-to-def      │
                        └─────────────────┘
```

### Commands

| Command | Description |
|---------|-------------|
| `Beethoven: Regenerate C++ Headers` | Manually trigger header generation |
| `Beethoven: Refresh clangd Configuration` | Update clangd include paths |
| `Beethoven: Show Scala-C++ Symbol Mappings` | Display detected symbol mappings |

### Cross-Language Go-to-Definition

The extension maps C++ namespaces to Scala `AccelCommand` definitions:

**C++ usage:**
```cpp
TestSystem::matmul(core_id, wgt_addr, in_addr, out_addr);
```

**Jumps to Scala definition:**
```scala
class SystolicArrayCmd extends AccelCommand("matmul") {
  val wgt_addr = Address()
  val in_addr = Address()
  val out_addr = Address()
}
```

This works by parsing `beethoven_hardware.h` and matching against `AccelCommand("name")` patterns in Scala sources.

## IntelliJ IDEA for Scala

For heavy Scala/Chisel development, IntelliJ provides deeper IDE features than Metals.

### Setup

1. Install IntelliJ IDEA (Community or Ultimate)
2. Install the **Scala** plugin: Settings → Plugins → Marketplace → "Scala"
3. Open `Beethoven-Hardware` as an sbt project: File → Open → select the directory

IntelliJ will import the sbt build and index all dependencies.

### Useful Settings

**Enable Chisel/FIRRTL support:**
- Settings → Languages & Frameworks → Scala → Check "Use Scala 2.x compatible features"

**Improve build performance:**
- Settings → Build, Execution, Deployment → Build Tools → sbt
- Enable "Use sbt shell for project reload and builds"

### Running Hardware Generation

Create a Run Configuration:
1. Run → Edit Configurations
2. Add New → sbt Task
3. Tasks: `run`
4. Working directory: `<path>/Beethoven-Hardware`
5. Environment variables: `BEETHOVEN_PATH=<path>/Composer`

Now you can generate hardware with Run (Shift+F10).

### Debugging Elaboration

IntelliJ can debug the Scala elaboration process (when Chisel generates FIRRTL):

1. Set breakpoints in your Scala modules
2. Edit Configuration → check "Enable debugging"
3. Run → Debug (Shift+F9)

This helps diagnose issues in configuration code or module instantiation.

## CLion for C++ Testbenches

For C++ testbench development with CMake integration.

### Setup

1. Open your accelerator project (containing `CMakeLists.txt`)
2. CLion auto-detects CMake and configures the build

### CMake Configuration

Ensure your `CMakeLists.txt` uses Beethoven's CMake functions:

```cmake
find_package(beethoven REQUIRED)

beethoven_hardware(my_accel
  MAIN_CLASS com.example.MyAccelBuild
  PLATFORM discrete
)

beethoven_testbench(my_test
  SOURCES test.cc
  HARDWARE my_accel
  SIMULATOR verilator
)
```

CLion will index the generated `beethoven_hardware.h` automatically.

### Debugging Simulations

1. Set breakpoints in your C++ testbench
2. Run → Debug 'my_test'

You can step through host code while the simulation runs. Note that you can't step into Verilog; use waveform viewers for RTL debugging.

## Troubleshooting

### VSCode: Headers not regenerating
- Check `beethoven.mainClass` is set correctly
- Ensure Metals is running (check status bar)
- Try manual regeneration: Cmd+Shift+P → "Beethoven: Regenerate C++ Headers"

### VSCode: C++ completions missing
- Verify `.clangd` file exists with correct include paths
- Run "Beethoven: Refresh clangd Configuration"
- Restart clangd: "clangd: Restart language server"

### IntelliJ: sbt import fails
- Ensure JDK 11+ is configured: Settings → Build → Build Tools → sbt → JDK
- Delete `.idea` and `.bsp` directories and reimport

### CLion: CMake errors
- Set `BEETHOVEN_HARDWARE_PATH` environment variable
- Ensure `beethoven` package is installed: `sudo make install` in Beethoven-Software

## Summary

| IDE | Best For | Key Feature |
|-----|----------|-------------|
| VSCode + Beethoven ext | Mixed Scala/C++ workflows | Cross-language go-to-definition |
| IntelliJ | Heavy Scala development | Debuggable elaboration |
| CLion | C++ testbench focus | CMake integration |

For most users, VSCode with the Beethoven extension provides the best experience for iterating between hardware and software changes.

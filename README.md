# ARVO2.0 - C Language Build Agent

A specialized build agent for automatically building C projects using Docker containers.

## Overview

ARVO2.0 is a streamlined version focused exclusively on C language projects. It automatically:

1. Downloads C repositories from GitHub
2. Analyzes the build system (Makefile, CMakeLists.txt, or direct GCC)
3. Builds the project in a Docker container
4. Generates a reproducible Dockerfile

## Features

- **C-only focus**: No Python dependencies or complexity
- **Multiple build systems**: Supports make, cmake, and direct gcc compilation
- **Docker integration**: Uses `gcr.io/oss-fuzz-base/base-builder` for C build tools
- **LLM-powered**: Uses GPT-4 to intelligently determine build steps
- **Reproducible**: Generates Dockerfiles for consistent builds

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Build a C project
python build_agent/main.py owner/repo commit_sha /path/to/root
```

## Example

```bash
# Build a simple Hello World C project
python build_agent/main.py torvalds/linux abc123def456 /root/workspace
```

## Architecture

```
build_agent/
├── main.py                 # Main entry point
├── agents/
│   └── configuration.py    # C build configuration agent
├── tools/                  # C build tools
│   ├── run_make.py
│   ├── run_cmake.py
│   ├── run_gcc.py
│   └── apt_install.py
└── utils/
    ├── sandbox.py          # Docker container management
    ├── llm.py             # LLM interface
    ├── tools_config.py    # Tool definitions
    └── integrate_dockerfile.py  # Dockerfile generation
```

## Supported Build Systems

- **Make**: Projects with Makefile
- **CMake**: Projects with CMakeLists.txt  
- **Direct GCC**: Simple C files without build system

## Requirements

- Docker
- Python 3.8+
- OpenAI API key (for GPT-4)

## License

Apache License 2.0

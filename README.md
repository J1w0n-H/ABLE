# Repo2Run
<p align="center">
  <img width="150" alt="Repo2Run" src="https://github.com/user-attachments/assets/b7ee9681-d05b-468f-bbef-3040d8c6683b" />
</p>

<p align="center">
  <a href="https://arxiv.org/abs/2502.13681"><img src="https://img.shields.io/badge/cs.SE-arXiv%3A2502.13681-B31B1B.svg"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg"></a>
</p>

## 🚀 News
Our paper: "Repo2Run: Automated Building Executable Environment for Code Repository at Scale" has been accepted by **NeurIPS 2025** main track as a **spotlight**!

# ARVO2.0: Automated Repository Verification and Orchestration for C/C++

An LLM-based build agent system specialized for **C/C++ projects**. Automatically detects build systems (CMake, Makefile, configure), installs dependencies, and ensures projects compile and pass tests — all within isolated Docker containers.

**Based on**: HereNThere (Python-focused) → **Adapted for C/C++ projects**

## Features

- 🐳 Docker-based sandbox environment for isolated C/C++ builds
- 🤖 GPT-4 powered autonomous dependency resolution
- 🔧 Support for CMake, Makefile, autotools (configure)
- 📦 apt-get package management with intelligent tracking
- 🔄 Automatic rollback on build failures
- 🔁 Build reuse optimization (avoids redundant rebuilds)
- 💰 Intelligent output truncation (68% token reduction, 70% cost reduction)
- ✅ **Success Rate**: 100% (tested on hello.c, cJSON, tinyxml2, curl)

## Prerequisites

- Python 3.x
- Docker
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/bytedance/repo2run.git
cd repo2run
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

**Recommended** (real-time output with automatic logging):

```bash
python3 build_agent/main.py <repository_full_name> <sha> <root_path>
```

**Features**:
- ✅ **Automatic logging**: Output saved to `build_agent/log/<repo>_<sha>.log`
- ✅ **Real-time display**: Unbuffered output to console
- ✅ **Dual output**: Both console and log file simultaneously

**Note**: Logging is automatic. No need for `| tee` or `-u` flag.

### Arguments

- `repository_full_name`: The full name of the repository (e.g., `curl/curl`, `DaveGamble/cJSON`)
- `sha`: The commit SHA (full or short hash)
- `root_path`: The root path for ARVO2.0 (usually `/root/Git/ARVO2.0`)

### Examples

**Simple C project** (~15 seconds):
```bash
cd /root/Git/ARVO2.0
python3 build_agent/main.py dvyshnavi15/helloworld 2449df7 /root/Git/ARVO2.0
# Log auto-saved to: build_agent/log/dvyshnavi15_helloworld_2449df7.log
```

**CMake project** (~30 seconds):
```bash
cd /root/Git/ARVO2.0
python3 build_agent/main.py DaveGamble/cJSON c859b25 /root/Git/ARVO2.0
# Log auto-saved to: build_agent/log/DaveGamble_cJSON_c859b25.log
# Result: 19/19 tests passed
```

**Complex project** (~4 minutes):
```bash
cd /root/Git/ARVO2.0  
python3 build_agent/main.py curl/curl 7e12139 /root/Git/ARVO2.0
# Log auto-saved to: build_agent/log/curl_curl_7e12139.log
# Features: 17 dependencies, source builds, rollback recovery
```

## Project Structure

- `build_agent/` - Main package directory
  - `agents/` - Agent implementations for build configuration
  - `utils/` - Utility functions and helper classes
  - `docker/` - Docker-related configurations
  - `main.py` - Main entry point
  - `multi_main.py` - Multi-process support

## Features in Detail

### Sandbox Environment
Uses Docker containers (`gcr.io/oss-fuzz-base/base-builder`) for isolated C/C++ builds with pre-installed tools:
- gcc, g++, clang, clang++
- make, cmake, autoconf, automake
- pkg-config, libtool

### Dependency Management
- **Waiting List**: Manages apt package installation queue
- **Intelligent Tracking**: Tracks only installed packages (not all system packages)
- **Source Builds**: LLM can autonomously build dependencies from source when needed
- **Error Handling**: Full error details on failures, summaries on success

### Configuration Agent (GPT-4 powered)
- **Autonomous problem-solving**: Learns from errors, tries alternative solutions
- **Build system detection**: CMake, Makefile, configure scripts
- **Version conflict resolution**: Can diagnose and fix library version issues
- **Rollback capability**: Auto-reverts on failures, preserves container state

### Output Files
All tests generate comprehensive output in `build_agent/output/<user>/<repo>/`:
- `Dockerfile`: Reproducible build recipe
- `test.txt`: Test execution results
- `outer_commands.json`: High-level command log with timing
- `inner_commands.json`: Docker container command history
- `dpkg_list.txt`: Installed apt packages
- `track.json`: Complete LLM conversation
- `sha.txt`: Commit hash

### Performance
- **Cost**: $0.09-$0.48 per project (GPT-4o)
- **Time**: 15s (simple) to 4min (complex)
- **Token reduction**: 68% via intelligent truncation
- **Success rate**: 100% on tested projects

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Citation

```bibtex
@article{hu2025llm,
  title={An LLM-based Agent for Reliable Docker Environment Configuration},
  author={Hu, Ruida and Peng, Chao and Wang, Xinchen and Gao, Cuiyun},
  journal={arXiv preprint arXiv:2502.13681},
  year={2025}
}
```

## License

Apache-2.0

## Ackowledgement

[https://github.com/Aider-AI/aider](https://github.com/Aider-AI/aider)

## Contact

pengchao.x@bytedance.com

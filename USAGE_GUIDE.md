# ABLE Usage Guide

Complete reference for all ABLE commands and usage scenarios.

---

## 📋 Command Reference

### able build

Build a C/C++ project in Docker container.

**Syntax:**
```bash
able build <REPOSITORY> <COMMIT> [OPTIONS]
```

**Arguments:**
- `REPOSITORY` - GitHub repository (e.g., `ImageMagick/ImageMagick`)
- `COMMIT` - Git commit SHA (e.g., `336f2b8`)

**Options:**
- `--model TEXT` - LLM model to use (default: `gpt-4.1-mini`)
- `--max-turns INT` - Maximum iterations (default: `100`)
- `--output PATH` - Output directory (default: `./output`)
- `--timeout INT` - Timeout in seconds (default: `14400`)
- `--root-path PATH` - Root directory (default: `.`)
- `--verbose` - Enable verbose logging
- `--debug` - Enable debug mode

**Examples:**
```bash
# Basic build
able build ImageMagick/ImageMagick 336f2b8

# Use GPT-4 for complex projects
able build FFmpeg/FFmpeg abc1234 --model gpt-4

# Increase iterations for difficult builds
able build curl/curl d9cecdd --max-turns 200

# Verbose output for debugging
able build project/repo sha --verbose --debug

# Custom output directory
able build project/repo sha --output ./my_builds

# Combine multiple options
able build curl/curl d9cecdd \
  --model gpt-4 \
  --max-turns 150 \
  --verbose \
  --output ./curl_builds
```

---

### able config

Show current configuration and verify setup.

**Syntax:**
```bash
able config
```

**Output:**
```
📋 ABLE Configuration
======================================================================

LLM Settings:
  Model:        gpt-4.1-mini
  Max turns:    100
  Timeout:      14400s

Docker Settings:
  Image:        gcr.io/oss-fuzz-base/base-builder

Paths:
  Output:       ./output

🔑 API Keys:
  OpenAI:       ✅ Configured
  Anthropic:    ❌ Not configured
```

**Use Cases:**
- Verify API keys are configured
- Check current settings before build
- Troubleshoot configuration issues

---

### able verify

Verify a generated Dockerfile can be built.

**Syntax:**
```bash
able verify <DOCKERFILE> [OPTIONS]
```

**Arguments:**
- `DOCKERFILE` - Path to Dockerfile

**Options:**
- `--build-test` - Actually build the Docker image (10 min timeout)

**Examples:**
```bash
# Check Dockerfile syntax
able verify build_agent/output/curl/curl/Dockerfile

# Build test (verify it actually works)
able verify build_agent/output/curl/curl/Dockerfile --build-test
```

---

### able clean

Clean build artifacts, caches, and Docker resources.

**Syntax:**
```bash
able clean [OPTIONS]
```

**Options:**
- `--output` - Remove output directory
- `--logs` - Remove log files
- `--docker` - Clean Docker containers and images
- `--cache` - Clear repository cache
- `--all` - Remove everything (confirmation required)
- `--force` - Skip confirmation prompts

**Examples:**
```bash
# Remove output directory
able clean --output

# Clean Docker resources
able clean --docker

# Clear repository cache
able clean --cache

# Remove everything (with confirmation)
able clean --all

# Force clean without confirmation
able clean --all --force
```

---

### able version

Show version information.

**Syntax:**
```bash
able version
```

**Output:**
```
ABLE 1.0.0
LLM-Driven Build Automation for C/C++ Projects
Copyright (2025) Bytedance Ltd.
```

---

## 🎯 Usage Scenarios

### Scenario 1: First Time Setup

```bash
# 1. Install
pip install -e .

# 2. Configure
cp .env.example .env
nano .env  # Add OPENAI_API_KEY

# 3. Verify
able config

# 4. Test build
able build ImageMagick/ImageMagick 336f2b8
```

---

### Scenario 2: Vulnerability Reproduction

```bash
# Build at vulnerable commit
able build project/repo <vulnerable-commit>

# Check generated Dockerfile
cat build_agent/output/project/repo/Dockerfile

# Verify it builds correctly
able verify build_agent/output/project/repo/Dockerfile --build-test

# Use for vulnerability testing
docker build -t vuln-test build_agent/output/project/repo/
docker run -it vuln-test bash
```

---

### Scenario 3: Batch Testing

```bash
# Test multiple commits
for commit in abc123 def456 ghi789; do
    echo "Building commit: $commit"
    able build project/repo $commit
    
    # Check if successful
    if [ -f "build_agent/output/project/repo/Dockerfile" ]; then
        echo "✅ Success: $commit"
    else
        echo "❌ Failed: $commit"
    fi
done
```

---

### Scenario 4: Fuzzing Preparation

```bash
# 1. Build project
able build target/project latest

# 2. Verify Dockerfile
able verify build_agent/output/target/project/Dockerfile --build-test

# 3. Add fuzzing harness
cd build_agent/output/target/project/
cat >> Dockerfile << 'EOF'
# Add fuzzing harness
COPY fuzz_target.cc /repo/
RUN clang++ -fsanitize=fuzzer fuzz_target.cc -o fuzz_target
EOF

# 4. Build fuzzing image
docker build -t fuzz-target .
```

---

### Scenario 5: CI/CD Integration

```bash
# In your CI pipeline
jobs:
  build-check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Setup ABLE
        run: |
          pip install -e .
          echo "OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" > .env
      
      - name: Build project
        run: |
          able build project/repo ${{ github.sha }}
      
      - name: Verify Dockerfile
        run: |
          able verify build_agent/output/project/repo/Dockerfile
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dockerfile
          path: build_agent/output/project/repo/Dockerfile
```

---

### Scenario 6: Debugging Build Failures

```bash
# 1. Run with verbose output
able build project/repo sha --verbose --debug

# 2. Check logs
tail -f build_agent/output/project/repo/*.log

# 3. Inspect LLM conversation
cat build_agent/output/project/repo/track.json | jq .

# 4. Check executed commands
cat build_agent/output/project/repo/inner_commands.json | jq .

# 5. Try different model
able build project/repo sha --model gpt-4

# 6. Increase iterations
able build project/repo sha --max-turns 200
```

---

## 🔧 Advanced Configuration

### Environment Variables

Create `.env` file:
```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional
ABLE_LLM_MODEL=gpt-4.1-mini
ABLE_MAX_TURN=100
ABLE_OUTPUT_ROOT=./output
ABLE_TIMEOUT=14400
ABLE_VERBOSE=false
ABLE_DEBUG=false

# Docker settings
ABLE_DOCKER_IMAGE=gcr.io/oss-fuzz-base/base-builder
ABLE_MEMORY_LIMIT=8g
ABLE_CPU_LIMIT=4

# Repository cache
ABLE_REPO_CACHE=./build_agent/utils/repo
```

### Runtime Overrides

```bash
# Override with environment variables
ABLE_LLM_MODEL=gpt-4 able build project/repo sha

# Or use CLI options
able build project/repo sha --model gpt-4
```

---

## 📊 Output Files

After build completes:

```
build_agent/output/<AUTHOR>/<REPO>/
├── <REPO>_<SHA>.log              # Complete execution log
├── Dockerfile                     # Reproducible build recipe
├── track.json                     # LLM conversation history
├── inner_commands.json            # Commands executed in Docker
├── outer_commands.json            # Docker management commands
├── test.txt                       # Build verification result
├── sha.txt                        # Commit SHA
└── dpkg_list.txt                  # Installed packages list
```

### File Descriptions

- **`<REPO>_<SHA>.log`** - Full stdout/stderr output, useful for debugging
- **`Dockerfile`** - Use this to reproduce the build anywhere
- **`track.json`** - See how LLM solved problems step-by-step
- **`inner_commands.json`** - All commands executed inside Docker
- **`test.txt`** - Contains "Congratulations" if build succeeded
- **`dpkg_list.txt`** - List of all installed apt packages

---

## 💡 Tips & Tricks

### 1. Speed Up Builds with Caching

```bash
# First build: ~10 minutes (clone + build)
able build FFmpeg/FFmpeg abc1234

# Same commit again: instant! (cache hit)
able build FFmpeg/FFmpeg abc1234

# Different commit: ~30 seconds (fetch only)
able build FFmpeg/FFmpeg xyz5678
```

**Cache location:** `build_agent/utils/repo/<author>/<repo>/repo/`

### 2. Monitor Progress

```bash
# Run build in one terminal
able build project/repo sha --verbose

# Watch logs in another terminal
tail -f build_agent/output/project/repo/*.log
```

### 3. Reuse Dockerfile

```bash
# After successful build
cd build_agent/output/project/repo/

# Build Docker image
docker build -t my-project .

# Run container
docker run -it my-project bash
```

### 4. Batch Testing

```bash
# Test multiple projects
projects=(
    "ImageMagick/ImageMagick:336f2b8"
    "curl/curl:d9cecdd"
    "FFmpeg/FFmpeg:abc1234"
)

for proj in "${projects[@]}"; do
    IFS=':' read -r repo commit <<< "$proj"
    able build "$repo" "$commit"
done
```

### 5. Clean Up Periodically

```bash
# Clean Docker to free space
able clean --docker

# Clear old caches
able clean --cache

# Remove old outputs
able clean --output
```

---

## 🐛 Troubleshooting

### Build Fails

```bash
# 1. Check logs
tail -100 build_agent/output/project/repo/*.log

# 2. Try different model
able build project/repo sha --model gpt-4

# 3. Increase iterations
able build project/repo sha --max-turns 200

# 4. Check configuration
able config
```

### API Key Issues

```bash
# Verify API key
able config

# Re-configure
nano .env
# Add: OPENAI_API_KEY=sk-...
```

### Docker Issues

```bash
# Check Docker
docker ps

# Restart Docker
sudo systemctl restart docker

# Clean Docker resources
able clean --docker
```

---

## 📚 Getting More Help

```bash
# General help
able --help

# Command-specific help
able build --help
able clean --help
able verify --help

# Show version
able version

# Check configuration
able config
```

---

**For installation and setup, see README.md**


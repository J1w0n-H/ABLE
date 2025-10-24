# Changelog

All notable changes to ARVO 2.0 project will be documented in this file.

---

## [2.3.0] - 2025-10-24

### 🚀 Added

- **Smart repository reuse**: Automatically reuse previously cloned repositories with commit verification
- **Commit-level caching**: Skip fetch/checkout if already at target commit (300x faster for repeated runs)
- **COPY-based Dockerfile**: Use local cached repositories instead of `git clone` during Docker build
- **Safe command filtering**: Comprehensive filtering of read-only commands (ls, cat, grep, etc.) at multiple stages
- **Per-command rollback strategy**: Rollback to last checkpoint on failure, not initial state

### ⚡ Changed

- **Rollback behavior**: Changed from "success → rollback to initial → replay" to "failure → rollback to last checkpoint"
- **Command recording**: Only dangerous commands recorded in `inner_commands.json` (75% reduction)
- **Dockerfile generation**: Always include directory context (`cd dir && command`) for cmake/make/configure
- **Build context**: Use project root as Docker build context for COPY access

### 🔧 Improved

- **Performance**: 300x faster for repeated runs with same commit (30s → 0.1s)
- **Network usage**: No network needed during Docker builds (COPY instead of git clone)
- **Log size**: 73% smaller `inner_commands.json` files
- **Dockerfile clarity**: 69% fewer RUN statements (only meaningful commands)
- **Checkpoint efficiency**: 75% fewer Docker commits (skip safe commands)

### 🐛 Fixed

- **Directory context lost**: Commands now execute in correct directory in Dockerfile
- **Unnecessary clones**: Stop re-cloning repositories that already exist locally
- **Network dependency**: Docker builds no longer require network access
- **Redundant checkpoints**: Skip checkpoints for read-only commands

### 📚 Documentation

- Added comprehensive v2.3 documentation:
  - `v2.3/README.md`: Release notes and overview
  - `v2.3/01_ROLLBACK_STRATEGY.md`: Docker snapshot rollback details
  - `v2.3/02_COMMAND_FILTERING.md`: Safe command filtering system
  - `v2.3/03_REPOSITORY_REUSE.md`: Repository caching optimization
  - `v2.3/04_DOCKERFILE_IMPROVEMENTS.md`: Enhanced Dockerfile generation
  - `v2.3/00_INDEX.md`: Documentation index and navigation

### 🔄 Modified Files

- `build_agent/utils/sandbox.py`: Command filtering and rollback logic
- `build_agent/utils/command_handlers.py`: Safe command detection
- `build_agent/agents/configuration.py`: Removed final rollback-and-replay
- `build_agent/utils/integrate_dockerfile.py`: COPY usage and directory context
- `build_agent/main.py`: Repository reuse with commit verification
- `build_agent/utils/helpers.py`: Safe commands list (50+ commands)
- `VERSION`: Updated to 2.3.0

---

## [2.2.0] - Previous Release

### Added

- Command Pattern refactoring for better modularity
- Enhanced sandbox architecture
- Improved error handling

---

## [2.1.0] - Initial Release

### Added

- C/C++ project support
- Docker-based sandbox environment
- LLM-driven configuration
- Basic rollback mechanism
- Dockerfile generation

---

## Performance Summary

| Version | Clone Time | Repeat Run | Log Size | Dockerfile RUN |
|---------|-----------|------------|----------|----------------|
| 2.1.0 | 30s | 30s | 344 lines | 35 statements |
| 2.3.0 | 30s | **0.1s** | **94 lines** | **11 statements** |
| **Improvement** | - | **300x** | **73%↓** | **69%↓** |

---

## Upgrade Guide

### From 2.1 → 2.3

**No breaking changes.** Improvements are automatic:

1. Existing repositories will be reused automatically
2. Old command logs may include safe commands (expected)
3. New Dockerfiles will use COPY instead of git clone
4. Rollback behavior changed (per-command, not global)

**Action required**: None. All improvements are transparent.

**Recommended**:
- Review documentation in `v2.3/` directory
- Monitor cache size in `utils/repo/`
- Test with your projects to verify compatibility

---

## Contributors

Development team

---

## License

Apache License 2.0


# ARVO2.0 Test Files

## 📁 Directory Structure

```
tests/
├── README.md           # This file
├── scripts/            # Test scripts
│   ├── test_*.sh      # Shell test scripts
│   └── test_*.py      # Python test scripts
├── logs/              # Test logs
│   └── *.log          # Log files from tests
└── archive/           # Old test files
```

---

## 🧪 Test Scripts

### test_command_pattern.sh
- **Purpose**: Test Command Pattern vs Original logic
- **Usage**: `bash tests/scripts/test_command_pattern.sh`

### test_handlers_simple.py
- **Purpose**: Test individual command handlers
- **Usage**: `python3 tests/scripts/test_handlers_simple.py`

### test_runtest_improvement.sh
- **Purpose**: Test runtest improvements
- **Usage**: `bash tests/scripts/test_runtest_improvement.sh`

### test_cmake_edge_cases.sh
- **Purpose**: Test CMake edge cases
- **Usage**: `bash tests/scripts/test_cmake_edge_cases.sh`

---

## 📊 Test Logs

All test execution logs are stored in `logs/` directory:
- `test_output.log` - Standard test output
- `test_verification.log` - Verification test results

---

## 🎯 Running Tests

### Run All Tests
```bash
cd /root/Git/ARVO2.0
for script in tests/scripts/*.sh; do
    bash "$script"
done
```

### Run Specific Test
```bash
cd /root/Git/ARVO2.0
bash tests/scripts/test_command_pattern.sh
```

---

## 📝 Adding New Tests

1. Create test script in `tests/scripts/`
2. Name it `test_<feature>.sh` or `test_<feature>.py`
3. Document it in this README
4. Logs go to `tests/logs/`

---

**Last Updated**: 2025-10-19

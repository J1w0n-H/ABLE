# Rollback Strategy - ARVO 2.3

## Overview

ARVO 2.3 implements a **per-command checkpoint rollback** strategy instead of the previous "rollback-to-initial-and-replay" approach.

---

## Previous Strategy (v2.1)

```
Command 1 → Success → Save
Command 2 → Success → Save  
Command 3 → Success → Save
Command 4 (runtest) → Success!
    ↓
Rollback to initial state
Replay Command 1, 2, 3 in clean environment
Verify clean build
```

**Problems**:
- Unnecessary rollback even on success
- Time-consuming replay
- Extra verification steps

---

## New Strategy (v2.3)

```
Command 1:
  ├─ Create checkpoint A
  ├─ Execute
  ├─ Success → Continue
  
Command 2:
  ├─ Create checkpoint B
  ├─ Execute
  ├─ **Fail** → Rollback to checkpoint B
  └─ LLM retries different approach

Command 2 (retry):
  ├─ Create checkpoint B'
  ├─ Execute  
  ├─ Success → Continue
  
Command 3:
  ├─ Create checkpoint C
  ├─ Execute
  ├─ Success → Continue

Final success → Complete (no rollback)
```

**Benefits**:
- Rollback only on failure
- Minimal rollback (to previous checkpoint, not initial)
- No unnecessary replay on success
- Faster overall execution

---

## Implementation

### Checkpoint Creation (`commit_container`)

```python
def commit_container(self):
    # Create Docker image snapshot
    image = self.container.commit(
        repository=f"{self.full_name}",
        tag='tmp'
    )
```

**What's saved**:
- Entire filesystem state
- Installed packages
- Environment variables
- Compiled binaries
- All file modifications

### Rollback (`switch_to_pre_image`)

```python
def switch_to_pre_image(self):
    # Stop current container
    self.container.stop()
    self.container.remove()
    
    # Start new container from checkpoint
    self.container = self.client.containers.run(
        tmp_image_name,  # Last checkpoint
        detach=True,
        ...
    )
```

**Result**: System restored to exact state before failed command

---

## When Rollback Happens

### ✅ Rollback Triggered

```python
# Command fails and is not a safe command
if return_code != 0 and not is_safe:
    session.sandbox.switch_to_pre_image()
```

Examples:
- `make` fails → Rollback
- `cmake ..` fails → Rollback  
- `apt-get install` fails → Rollback

### ❌ No Rollback

```python
# Safe commands (ls, cat, grep)
if is_safe:
    # Execute but don't create checkpoint
    # Don't rollback on failure
```

Examples:
- `ls /repo` fails → No rollback (just shows error)
- `cat file.txt` fails → No rollback
- `grep pattern file` fails → No rollback

---

## Comparison: Git vs Docker Rollback

| Aspect | Git Rollback | Docker Snapshot (ARVO) |
|--------|--------------|------------------------|
| **Scope** | Code only | Entire filesystem |
| **Packages** | ❌ Not restored | ✅ Restored |
| **Env vars** | ❌ Not restored | ✅ Restored |
| **Binaries** | ❌ Not restored | ✅ Restored |
| **System config** | ❌ Not restored | ✅ Restored |
| **Speed** | Fast | Medium |

**Why Docker?**
- Need to restore `apt-get install` effects
- Need to restore compiled binaries
- Need to restore system configuration
- Complete environment rollback, not just code

---

## Example Scenario

### Build Attempt 1 (Fails)

```bash
Checkpoint 0: Initial state
    ↓
Command: cmake .. -DCMAKE_BUILD_TYPE=Release
    → Create Checkpoint 1
    → Execute
    → **FAIL** (missing dependency)
    → Rollback to Checkpoint 1
    
LLM: "Need to install libssl-dev first"
```

### Build Attempt 2 (Success)

```bash
Start from: Checkpoint 1 (before cmake)
    ↓
Command: apt-get install libssl-dev
    → Create Checkpoint 2
    → Execute
    → Success ✅
    
Command: cmake .. -DCMAKE_BUILD_TYPE=Release
    → Create Checkpoint 3
    → Execute
    → Success ✅
    
Command: make -j4
    → Create Checkpoint 4
    → Execute
    → Success ✅
    
Final success → Complete (no rollback needed)
```

---

## Performance Impact

| Scenario | Time Impact |
|----------|-------------|
| Checkpoint creation | ~1-2 seconds per command |
| Rollback operation | ~3-5 seconds |
| No rollback (success) | **0 seconds** (v2.3) vs ~30 seconds (v2.1) |

**Net result**: Faster on success, similar on failure.

---

## Code Locations

### Checkpoint Creation

**File**: `build_agent/utils/sandbox.py`

```python
# Line 462-463
if not (command.split()[0].strip() in safe_cmd and '>' not in command):
    self.sandbox.commit_container()
```

### Rollback on Failure

**File**: `build_agent/utils/sandbox.py`

```python
# Line 534-536
if not (command.split()[0].strip() in safe_cmd and '>' not in command):
    self.sandbox.switch_to_pre_image()
    output_lines.append('The command execution failed, so I have reverted it back to the previous state.')
```

**File**: `build_agent/utils/command_handlers.py`

```python
# Line 427-429
if not is_safe:
    session.sandbox.switch_to_pre_image()
    output_lines.append('The command execution failed, so I have reverted it back to the previous state.')
```

---

## Best Practices

1. **Safe Commands**: Use grep, ls, cat freely - no performance penalty
2. **Checkpoint Frequency**: Automatic - one per dangerous command
3. **Disk Management**: Old checkpoints are automatically cleaned up
4. **Debugging**: Check `inner_commands.json` for command history

---

## Future Improvements

Potential optimizations for v2.4+:
- Incremental checkpoints (layered)
- Checkpoint garbage collection
- Checkpoint compression
- Parallel checkpoint creation


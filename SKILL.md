---
name: ep133-pak
description: |
  Create and manipulate Teenage Engineering EP-133 K.O. II sampler project files (.ppak/.pak).
  Use when: (1) Creating beats/patterns for EP-133, (2) Generating .ppak project files,
  (3) Assigning samples to pads, (4) Programming drum patterns and sequences,
  (5) Working with EP-133 backup files. Triggers: EP-133, KO2, K.O. II, .ppak, .pak, sampler project.
---

# EP-133 K.O. II Project File Creator

Create `.ppak` project files for the Teenage Engineering EP-133 K.O. II sampler.

## Device Specifications (Official)

- **Memory**: 64 MB sampler/composer
- **Sample Slots**: 999
- **Pads**: 12 sample pads × 4 groups (A, B, C, D) = 48 total
- **Sequencer Resolution**: 96 PPQN (ticks per quarter note)
- **Audio**: 24-bit, SNR 96-98 dBA
- **MIDI**: Type A compliant (MMA), opto-coupled input
- **Sync**: 8th, 16th, 24 PPQN modes
- **Current OS**: 2.0.5 (Dec 2025)
- **Effects**: Delay, Reverb, Distortion, Chorus, Filter, Compressor + Punch-in FX 2.0

## File Format Overview

A `.ppak` file is a ZIP archive with paths starting with `/` (leading slash required):

```
.ppak (ZIP)
├── /meta.json
├── /projects/P01.tar    (or P02-P09)
└── /sounds/*.wav
```

The project tar contains:
```
P0X.tar
├── pads/a/p01-p12      (Group A pad assignments)
├── pads/b/p01-p12      (Group B pad assignments)
├── pads/c/p01-p12      (Group C pad assignments)
├── pads/d/p01-p12      (Group D pad assignments)
├── patterns/a01        (Pattern for Group A)
├── patterns/b01        (Pattern for Group B)
├── patterns/c01        (Pattern for Group C)
├── patterns/d01        (Pattern for Group D)
└── settings
```

## Critical Encoding Details

### Pattern Events (8 bytes each)

```
Bytes 0-1: Time position (uint16 little-endian, 0-383 for one bar)
Byte 2:    Row byte (pad number: 0x00=pad1, 0x08=pad2, ... 0x58=pad12)
Byte 3:    Column byte (always 0x3c for standard playback)
Byte 4:    Velocity (0-127)
Bytes 5-7: Flags (typically 0x10 0x00 0x00)
```

### Group/Pattern Relationship

**The pattern FILE determines which group's samples play:**
- `patterns/a01` → plays Group A samples
- `patterns/b01` → plays Group B samples
- `patterns/c01` → plays Group C samples
- `patterns/d01` → plays Group D samples

The column byte (0x3c) does NOT determine the group - it's typically fixed at 60.

### Pad File Format (27 bytes)

Sample assignment is at bytes 1-2 (uint16 little-endian):
```python
data[1:3] = struct.pack('<H', sample_number)
```

### Timing Reference (Official: 96 PPQN)

The EP-133 uses **96 ticks per quarter note (PPQN)** internally (per official Technical Specifications).

| Duration | Ticks |
|----------|-------|
| 1 bar (4/4) | 384 |
| 1 beat (quarter note) | 96 |
| 8th note | 48 |
| 16th note | 24 |
| 32nd note | 12 |
| Triplet 8th | 32 |
| Triplet 16th | 16 |

This matches standard MIDI resolution and allows precise swing/groove programming.

## Implementation

Use `scripts/create_ppak.py` for project creation. See `references/format-details.md` for complete binary specifications.

### Quick Example

```python
from create_ppak import EP133Project

project = EP133Project(device_sku="TE032AS001")

# Assign samples to pads
project.assign_sample('a', 10, 1)    # Pad 10 in Group A = sample #1
project.assign_sample('a', 7, 100)   # Pad 7 in Group A = sample #100

# Create pattern events: (time, pad, velocity)
project.add_event('a01', 0, 10, 127)      # Kick on beat 1
project.add_event('a01', 96, 7, 120)      # Snare on beat 2
project.add_event('a01', 192, 10, 127)    # Kick on beat 3
project.add_event('a01', 288, 7, 120)     # Snare on beat 4

project.save('/path/to/output.ppak', sounds_dir='/path/to/sounds')
```

## Common Patterns

### 4-on-the-floor (House)
```python
for beat in [0, 96, 192, 288]:
    project.add_event('a01', beat, kick_pad, 127)
```

### Boom-bap groove
```python
project.add_event('a01', 0, kick, 120)
project.add_event('a01', 144, kick, 90)   # Swung ghost
project.add_event('a01', 192, kick, 115)
project.add_event('a01', 96, snare, 127)
project.add_event('a01', 288, snare, 127)
```

### Hi-hat rolls (16ths)
```python
for i in range(16):
    vel = 100 if i % 2 == 0 else 70
    project.add_event('a01', i * 24, hihat, vel)
```

## Device SKU

The meta.json requires matching `device_sku` and `base_sku`. Get from user's backup file or use common value `TE032AS001`.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "SKUS DOES NOT MATCH" | Wrong device_sku in meta.json | Use SKU from user's backup |
| "PAK FILE IS EMPTY" | Missing leading slashes in ZIP paths | Use `/projects/P01.tar` not `projects/P01.tar` |
| Device crash | Invalid byte values in patterns | Use only documented encoding values |
| No sound on playback | Wrong pattern file for group | Put Group B events in `patterns/b01`, not `patterns/a01` |

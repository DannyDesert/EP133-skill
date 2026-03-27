# EP-133 File Format Complete Reference

## Official Device Specifications

Per the Teenage Engineering EP-133 User Guide (v2.0.5):

| Specification | Value |
|---------------|-------|
| Memory | 64 MB |
| Sample Slots | 999 |
| Pads | 12 × 4 groups |
| Sequencer Resolution | **96 PPQN (ticks per quarter note)** |
| Audio Input | 24-bit, SNR 96 dBA |
| Audio Output | 24-bit, SNR 98 dBA |
| MIDI | MMA Type A compliant |
| Sync | 8th, 16th, 24 PPQN modes |

Source: https://teenage.engineering/guides/ep-133/tech-specs

## meta.json Structure

```json
{
  "info": "teenage engineering - pak file",
  "pak_version": 1,
  "pak_type": "user",
  "pak_release": "1.2.0",
  "device_name": "EP-133",
  "device_sku": "TE032AS001",
  "device_version": "2.0.5",
  "generated_at": "2026-01-21T17:00:00.000Z",
  "author": "Claude",
  "base_sku": "TE032AS001"
}
```

**Critical**: `device_sku` and `base_sku` must match the target device. Extract from user's backup file.

## Pattern File Binary Format

### Header (4 bytes)
```
Byte 0: 0x00 (constant)
Byte 1: 0x01 (constant)
Byte 2: Number of events (uint8, max 255)
Byte 3: 0x00 (constant)
```

### Event Structure (8 bytes each)
```
Offset  Size  Type      Description
------  ----  --------  -----------
0       2     uint16LE  Time position (0-383 ticks per bar)
2       1     uint8     Row byte (pad file number identifier)
3       1     uint8     Column byte (0x3c = 60 for normal playback)
4       1     uint8     Velocity (0-127)
5       3     bytes     Flags (typically 0x10 0x00 0x00)
```

### Row Byte to Pad File Mapping
```
Pad file 1  = 0x00 (0)
Pad file 2  = 0x08 (8)
Pad file 3  = 0x10 (16)
Pad file 4  = 0x18 (24)
Pad file 5  = 0x20 (32)
Pad file 6  = 0x28 (40)
Pad file 7  = 0x30 (48)
Pad file 8  = 0x38 (56)
Pad file 9  = 0x40 (64)
Pad file 10 = 0x48 (72)
Pad file 11 = 0x50 (80)
Pad file 12 = 0x58 (88)
```

Formula: `row_byte = (pad_file_number - 1) * 8`

**Note**: Pattern events use pad *file* numbers, not labeled pad numbers. See Pad Layout section.

### Column Byte

For standard drum playback, always use `0x3c` (60).

Other values may represent chromatic pitch offsets but can cause issues. Stick to 0x3c unless experimenting.

## Pad Layout — Labeled vs File Numbers

The pad numbers printed on the device (labeled) do **not** match the pad file numbers (p01–p12) used in the tar archive. The bottom two rows of the 4×3 grid are swapped.

Physical grid (4 rows × 3 columns):
```
Row 1 (top):    file p01  p02  p03   ←→  labeled  7   8   9
Row 2:          file p04  p05  p06   ←→  labeled  4   5   6
Row 3:          file p07  p08  p09   ←→  labeled  1   2   3
Row 4 (bottom): file p10  p11  p12   ←→  labeled 10  11  12
```

Full mapping:

| Labeled | File | Labeled | File |
|---------|------|---------|------|
| 1  | p07 | 7  | p01 |
| 2  | p08 | 8  | p02 |
| 3  | p09 | 9  | p03 |
| 4  | p04 | 10 | p10 |
| 5  | p05 | 11 | p11 |
| 6  | p06 | 12 | p12 |

Formula for labeled pads 1–9: `file = labeled + 6` if labeled ≤ 3, else `labeled - 6` if labeled ≥ 7, else `labeled`.
Labeled pads 10–12 map directly to files p10–p12.

`create_ppak.py` exports `LABEL_TO_PAD_FILE` and `PAD_FILE_TO_LABEL` dicts for this conversion.

## Pad File Binary Format (27 bytes)

```
Offset  Size  Description
------  ----  -----------
0       1     Unknown (observed as 0x00)
1       2     Sample number (uint16LE, 0 = no sample)
3       5     Unknown (observed as 0x00)
8       2     Sample ROM ID (uint16LE) — see below
10      2     Unknown (observed as 0x00)
12      4     Project BPM (float32LE) — device writes this on sample assignment
16      1     Volume (0–100; default 100 = full volume)
17      3     Unknown (observed as 0x00)
20      1     Unknown (0xff in all observed pads)
21      3     Unknown (observed as 0x00)
24      1     Pan (0–127; default 60 = center)
25      2     Unknown (observed as 0x00)
```

### Sample ROM ID (bytes 8–9)

A uint16 little-endian value the device uses to locate the sample's audio data in ROM.
**A pad with a valid sample number but a zero ROM ID will show the correct sample name but produce no sound.**

Properties (reverse-engineered from device backups):
- Determined solely by sample number — pad number and group have no effect.
- Cannot be derived arithmetically from the sample number; it is a ROM address.
- The device's internal storage order differs from the user-facing category numbering:
  samples are stored **hats → snares → kicks** (reverse of the 200s/100s/1s scheme).
- Within each category, higher sample number = higher ROM offset (sequential storage).
- The slope (ROM units per sample number) differs across categories, reflecting
  different average sample lengths: ~402 units/sample for hats, ~257 for kicks.

**Known values** (discovered by reassigning samples on device and diffing backups):

| Sample | Name | ROM ID (uint16 LE) | Bytes 8–9 |
|--------|------|--------------------|-----------|
| 1 | MICRO KICK | 22412 | (140, 87) |
| 31 | BOOMER KICK | 30133 | (181, 117) |
| 126 | SNARE OPEN | 18697 | (9, 73) |
| 203 | CLOSED HAT LO | 7558 | (134, 29) |
| 221 | OPEN HAT REAL | 14798 | (206, 57) |

**How to discover a new sample's ROM ID:**
1. Load a ppak with the desired sample assigned to any pad.
2. On the device, change that pad's sample assignment to any other sample, then back to the desired sample.
3. Take a project backup.
4. Extract bytes 8–9 from the pad file in the backup tar.
5. Add the value to `PAD_SAMPLE_IDS` in `create_ppak.py`.

### Volume and Group Project Volume

Per-pad volume (byte 16) and group project volume are separate controls:

- **Byte 16** (pad file): per-pad volume, 0–100. Default 100. Appears fixed in the pad file; the device does not update it when the user adjusts the sound-edit volume knob.
- **Group project volume** (settings file, float32 at offsets 24/72/120/168 for groups A/B/C/D): what the sound-edit volume knob actually controls. Range 0.0–1.0, default 1.0.

## Settings File (222 bytes)

Binary file. BPM and group volumes must be set; all other bytes default to the sentinel pattern below.

```
Offset  Size  Description
------  ----  -----------
0       4     Unknown (0x00)
4       4     BPM (float32LE)
8       16    Unknown (0x00)
24      48    Group A: 12 × float32LE (see below)
72      48    Group B: 12 × float32LE
120     48    Group C: 12 × float32LE
168     48    Group D: 12 × float32LE
216     6     Unknown
```

### Group Volume Block (48 bytes = 12 × float32)

Each group occupies 48 bytes starting at the offsets above.

- **float[0]** (first 4 bytes): group project volume, 0.0–1.0. Default 1.0.
- **float[5]**: pattern level (fader "level" assignment). Observed values vary.
- **All other floats**: use sentinel value **-1.0** (= `0x000080bf`) meaning "use device default".

Setting any of these to 0.0 instead of -1.0 will cause that parameter to be interpreted as zero (silent).

## Timing Reference (Official: 96 PPQN)

The EP-133 uses **96 ticks per quarter note** as its internal sequencer resolution. This is confirmed in the official Technical Specifications.

| Note Value | Ticks | At 120 BPM |
|------------|-------|------------|
| Whole note | 384   | 2000ms     |
| Half note  | 192   | 1000ms     |
| Quarter    | 96    | 500ms      |
| 8th note   | 48    | 250ms      |
| 16th note  | 24    | 125ms      |
| 32nd note  | 12    | 62.5ms     |
| Triplet 8th| 32    | 166ms      |

### Swing/Shuffle

For swing feel, offset alternate notes:
- Straight 8ths: 0, 48, 96, 144...
- Swung 8ths: 0, 52, 96, 148... (offset by ~4-8 ticks)

## ZIP Structure Requirements

**Critical**: All paths must start with `/` (leading slash)

```python
import zipfile

with zipfile.ZipFile('output.ppak', 'w', zipfile.ZIP_DEFLATED) as zf:
    # CORRECT - with leading slash
    info = zipfile.ZipInfo('/projects/P01.tar')
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, tar_data)

    # WRONG - will cause "PAK FILE IS EMPTY" error
    # zf.writestr('projects/P01.tar', tar_data)
```

## TAR Structure

Standard POSIX tar with no compression:

```python
import tarfile
import io

tar_buffer = io.BytesIO()
with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
    tar.add('pads')
    tar.add('patterns')
    tar.add('settings')
tar_data = tar_buffer.getvalue()
```

## Sound File Requirements

- Format: WAV (PCM)
- Sample rate: 44100 Hz recommended
- Bit depth: 16-bit or 24-bit
- Channels: Mono or Stereo
- Naming: `NNN name.wav` where NNN is 001-999

## Project Slots

EP-133 supports projects P01-P09. Specify in tar filename:
- `/projects/P01.tar` through `/projects/P09.tar`

## Complete Python Example

```python
import struct
import tarfile
import zipfile
import io
import json
import os

def create_pattern(events):
    """Create pattern binary from list of (time, pad_file_num, velocity) tuples"""
    if not events:
        return bytes([0x00, 0x01, 0x00, 0x00])

    events = sorted(events, key=lambda x: x[0])
    header = bytes([0x00, 0x01, len(events), 0x00])
    data = header

    for time, pad, velocity in events:
        row = (pad - 1) * 8   # pad is the FILE number, not the labeled number
        col = 0x3c
        event = struct.pack('<H', time) + bytes([row, col, velocity, 0x10, 0x00, 0x00])
        data += event

    return data
```

# EP-133 File Format Complete Reference

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
2       1     uint8     Row byte (pad identifier)
3       1     uint8     Column byte (0x3c = 60 for normal playback)
4       1     uint8     Velocity (0-127)
5       3     bytes     Flags (typically 0x10 0x00 0x00)
```

### Row Byte to Pad Mapping
```
Pad 1  = 0x00 (0)
Pad 2  = 0x08 (8)
Pad 3  = 0x10 (16)
Pad 4  = 0x18 (24)
Pad 5  = 0x20 (32)
Pad 6  = 0x28 (40)
Pad 7  = 0x30 (48)
Pad 8  = 0x38 (56)
Pad 9  = 0x40 (64)
Pad 10 = 0x48 (72)
Pad 11 = 0x50 (80)
Pad 12 = 0x58 (88)
```

Formula: `row_byte = (pad_number - 1) * 8`

### Column Byte

For standard drum playback, always use `0x3c` (60).

Other values may represent chromatic pitch offsets but can cause issues. Stick to 0x3c unless experimenting.

## Pad File Binary Format (27 bytes)

```
Offset  Size  Description
------  ----  -----------
0       1     Unknown (preserve from template)
1       2     Sample number (uint16LE, 0 = no sample)
3       24    Pad parameters (preserve from template)
```

### Assigning a Sample
```python
import struct

with open(pad_file, 'rb') as f:
    data = bytearray(f.read())

# Set sample number at bytes 1-2
data[1:3] = struct.pack('<H', sample_number)

with open(pad_file, 'wb') as f:
    f.write(data)
```

## Settings File (222 bytes)

Binary file containing project settings. Preserve from template/backup - do not modify unless you understand the format.

## Timing Reference

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
    """Create pattern binary from list of (time, pad, velocity) tuples"""
    if not events:
        return bytes([0x00, 0x01, 0x00, 0x00])

    events = sorted(events, key=lambda x: x[0])
    header = bytes([0x00, 0x01, len(events), 0x00])
    data = header

    for time, pad, velocity in events:
        row = (pad - 1) * 8
        col = 0x3c
        event = struct.pack('<H', time) + bytes([row, col, velocity, 0x10, 0x00, 0x00])
        data += event

    return data

def create_ppak(project_num, patterns, pad_assignments, sounds_dir, output_path,
                device_sku="TE032AS001", template_dir=None):
    """
    Create a complete .ppak file

    Args:
        project_num: 1-9
        patterns: dict of {'a01': [(time, pad, vel), ...], 'b01': [...], ...}
        pad_assignments: dict of {'a': {pad: sample, ...}, 'b': {...}, ...}
        sounds_dir: path to directory containing .wav files
        output_path: output .ppak path
        device_sku: device serial (get from user's backup)
        template_dir: optional path to template pads/settings
    """

    # Create working directory
    work_dir = '/tmp/ep133_work'
    os.makedirs(f'{work_dir}/pads/a', exist_ok=True)
    os.makedirs(f'{work_dir}/pads/b', exist_ok=True)
    os.makedirs(f'{work_dir}/pads/c', exist_ok=True)
    os.makedirs(f'{work_dir}/pads/d', exist_ok=True)
    os.makedirs(f'{work_dir}/patterns', exist_ok=True)

    # Create pad files (27 bytes each)
    pad_template = bytes([0x00] * 27)  # Minimal template
    for group in ['a', 'b', 'c', 'd']:
        for pad in range(1, 13):
            data = bytearray(pad_template)
            if group in pad_assignments and pad in pad_assignments[group]:
                sample = pad_assignments[group][pad]
                data[1:3] = struct.pack('<H', sample)
            with open(f'{work_dir}/pads/{group}/p{pad:02d}', 'wb') as f:
                f.write(data)

    # Create pattern files
    for pattern_name, events in patterns.items():
        with open(f'{work_dir}/patterns/{pattern_name}', 'wb') as f:
            f.write(create_pattern(events))

    # Create settings file (minimal)
    settings = bytes([0x00] * 222)
    with open(f'{work_dir}/settings', 'wb') as f:
        f.write(settings)

    # Create tar
    tar_buffer = io.BytesIO()
    os.chdir(work_dir)
    with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
        tar.add('pads')
        tar.add('patterns')
        tar.add('settings')
    tar_data = tar_buffer.getvalue()

    # Create meta.json
    meta = {
        "info": "teenage engineering - pak file",
        "pak_version": 1,
        "pak_type": "user",
        "pak_release": "1.2.0",
        "device_name": "EP-133",
        "device_sku": device_sku,
        "device_version": "2.0.5",
        "generated_at": "2026-01-21T12:00:00.000Z",
        "author": "Claude",
        "base_sku": device_sku
    }

    # Create final .ppak
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add tar with leading slash
        info = zipfile.ZipInfo(f'/projects/P{project_num:02d}.tar')
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, tar_data)

        # Add meta.json
        info = zipfile.ZipInfo('/meta.json')
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, json.dumps(meta, indent=2))

        # Add sounds
        for fname in os.listdir(sounds_dir):
            if fname.endswith('.wav'):
                with open(os.path.join(sounds_dir, fname), 'rb') as sf:
                    info = zipfile.ZipInfo(f'/sounds/{fname}')
                    info.compress_type = zipfile.ZIP_DEFLATED
                    zf.writestr(info, sf.read())

    return output_path
```

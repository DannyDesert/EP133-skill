#!/usr/bin/env python3
"""
EP-133 K.O. II Project File Creator

Creates .ppak files for the Teenage Engineering EP-133 sampler.
"""

import struct
import tarfile
import zipfile
import io
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional


# Mapping between labeled pad numbers (printed on device) and pad file numbers (p01-p12).
# The bottom two rows of pads are swapped: labeled 1-3 live in files 7-9 and vice versa.
# Row of 4-6 and row of 10-12 are unchanged.
LABEL_TO_PAD_FILE: Dict[int, int] = {
    1: 7,  2: 8,  3: 9,
    4: 4,  5: 5,  6: 6,
    7: 1,  8: 2,  9: 3,
    10: 10, 11: 11, 12: 12,
}
PAD_FILE_TO_LABEL: Dict[int, int] = {v: k for k, v in LABEL_TO_PAD_FILE.items()}


# Per-sample identifier bytes (8, 9) required for the device to locate sample audio.
# Without these a pad shows the correct sample name but produces no sound.
# Values are reverse-engineered by reassigning samples on device and diffing backups.
# Add new entries as they are discovered.
PAD_SAMPLE_IDS: Dict[int, Tuple[int, int]] = {
    1:   (140,  87),  # MICRO KICK
    31:  (181, 117),  # BOOMER KICK
    126: (  9,  73),  # SNARE OPEN
    203: (134,  29),  # CLOSED HAT LO
    221: (206,  57),  # OPEN HAT REAL
}


class EP133Project:
    """Create EP-133 project files (.ppak)"""

    def __init__(self, bpm: float, device_sku: str = "TE032AS001", project_num: int = 1,
                 base_sku: Optional[str] = None):
        """
        Initialize a new EP-133 project.

        Args:
            bpm: Project tempo in BPM (required — zero BPM causes "Error Clock" on device)
            device_sku: Device SKU (get from user's backup meta.json, e.g. "TE032AS002")
            project_num: Project slot 1-9
            base_sku: Hardware base SKU (get from user's backup meta.json, e.g. "TE032AS001").
                      Distinct from device_sku — get both from the backup's meta.json.
                      Defaults to device_sku if not provided.
        """
        self.bpm = float(bpm)
        self.device_sku = device_sku
        self.base_sku = base_sku if base_sku is not None else device_sku
        self.project_num = project_num
        self.pad_assignments: Dict[str, Dict[int, int]] = {
            'a': {}, 'b': {}, 'c': {}, 'd': {}
        }
        self.patterns: Dict[str, List[Tuple[int, int, int]]] = {
            'a01': [], 'b01': [], 'c01': [], 'd01': []
        }
        self._template_pads = None
        self._template_settings = None

    def load_template(self, backup_path: str):
        """
        Load pad and settings templates from an existing backup.
        This preserves pad parameters and settings that we don't fully understand.

        Args:
            backup_path: Path to .ppak or extracted backup directory
        """
        if backup_path.endswith('.ppak') or backup_path.endswith('.pak'):
            # Extract from archive
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(backup_path, 'r') as zf:
                    zf.extractall(tmpdir)
                # Find and extract tar
                for root, dirs, files in os.walk(tmpdir):
                    for f in files:
                        if f.endswith('.tar'):
                            tar_path = os.path.join(root, f)
                            with tarfile.open(tar_path, 'r') as tar:
                                tar.extractall(tmpdir)
                            break
                self._load_templates_from_dir(tmpdir)
        else:
            self._load_templates_from_dir(backup_path)

    def _load_templates_from_dir(self, dir_path: str):
        """Load templates from extracted directory"""
        self._template_pads = {}
        for group in ['a', 'b', 'c', 'd']:
            self._template_pads[group] = {}
            for pad in range(1, 13):
                pad_path = os.path.join(dir_path, 'pads', group, f'p{pad:02d}')
                if os.path.exists(pad_path):
                    with open(pad_path, 'rb') as f:
                        self._template_pads[group][pad] = bytearray(f.read())

        settings_path = os.path.join(dir_path, 'settings')
        if os.path.exists(settings_path):
            with open(settings_path, 'rb') as f:
                self._template_settings = f.read()

    def assign_sample(self, group: str, pad: int, sample_num: int):
        """
        Assign a sample to a pad.

        Args:
            group: 'a', 'b', 'c', or 'd'
            pad: Pad number 1-12
            sample_num: Sample number (matches filename prefix, e.g., 001, 100, 405)
        """
        if group not in ['a', 'b', 'c', 'd']:
            raise ValueError(f"Invalid group: {group}. Must be 'a', 'b', 'c', or 'd'")
        if not 1 <= pad <= 12:
            raise ValueError(f"Invalid pad: {pad}. Must be 1-12")
        self.pad_assignments[group][pad] = sample_num

    def add_event(self, pattern: str, time: int, pad: int, velocity: int = 100):
        """
        Add an event to a pattern.

        Args:
            pattern: Pattern name ('a01', 'b01', 'c01', 'd01')
            time: Time position in ticks (96 PPQN; one bar = 384 ticks).
                  Multi-bar patterns are valid — ticks beyond 383 are allowed.
            pad: Pad number 1-12
            velocity: Velocity 0-127 (default 100)

        Note: duplicate (time, pad) pairs are silently deduplicated on save,
        keeping the highest velocity event.
        """
        if pattern not in self.patterns:
            raise ValueError(f"Invalid pattern: {pattern}. Must be a01, b01, c01, or d01")
        if time < 0:
            raise ValueError(f"Invalid time: {time}. Must be >= 0")
        if not 1 <= pad <= 12:
            raise ValueError(f"Invalid pad: {pad}. Must be 1-12")
        if not 0 <= velocity <= 127:
            raise ValueError(f"Invalid velocity: {velocity}. Must be 0-127")

        self.patterns[pattern].append((time, pad, velocity))

    def add_kick(self, pattern: str, time: int, pad: int = 10, velocity: int = 127):
        """Convenience method for adding kick drum hits"""
        self.add_event(pattern, time, pad, velocity)

    def add_snare(self, pattern: str, time: int, pad: int = 7, velocity: int = 120):
        """Convenience method for adding snare hits"""
        self.add_event(pattern, time, pad, velocity)

    def add_hihat(self, pattern: str, time: int, pad: int = 5, velocity: int = 90):
        """Convenience method for adding hi-hat hits"""
        self.add_event(pattern, time, pad, velocity)

    def _create_pattern_data(self, events: List[Tuple[int, int, int]]) -> bytes:
        """Convert event list to binary pattern data"""
        if not events:
            return bytes([0x00, 0x01, 0x00, 0x00])

        # Deduplicate: for same (time, pad), keep highest velocity
        deduped: dict = {}
        for evt in events:
            key = (evt[0], evt[1])
            if key not in deduped or evt[2] > deduped[key][2]:
                deduped[key] = evt
        events = sorted(deduped.values(), key=lambda x: x[0])

        if len(events) > 255:
            raise ValueError(f"Too many events: {len(events)}. Maximum is 255")

        header = bytes([0x00, 0x01, len(events), 0x00])
        data = header

        for time, pad, velocity in events:
            row = (pad - 1) * 8
            col = 0x3c  # Standard playback
            event = struct.pack('<H', time) + bytes([row, col, velocity, 0x10, 0x00, 0x00])
            data += event

        return data

    def _create_pad_data(self, group: str, pad: int) -> bytes:
        """Create binary pad data"""
        # Use template if available
        if self._template_pads and group in self._template_pads and pad in self._template_pads[group]:
            data = bytearray(self._template_pads[group][pad])
        else:
            # 27-byte pad file with correct defaults (reverse-engineered from device backup)
            data = bytearray(27)
            # Bytes 8-9: sample-specific identifier — device needs this to locate audio data.
            # Without it the pad is silent even if the sample number is correct.
            # Values reverse-engineered by reassigning samples on device and diffing backups.
            sample_num = self.pad_assignments[group].get(pad, 0)
            sample_id = PAD_SAMPLE_IDS.get(sample_num, (0, 0))
            data[8]  = sample_id[0]
            data[9]  = sample_id[1]
            # Bytes 12-15: project BPM as float32 LE — device writes this on sample assignment.
            struct.pack_into('<f', data, 12, self.bpm)
            data[16] = 100   # volume
            data[20] = 255   # unknown — 0xff in all observed pads
            data[24] = 60    # pan center

        # Set sample number at bytes 1-2
        sample_num = self.pad_assignments[group].get(pad, 0)
        data[1:3] = struct.pack('<H', sample_num)

        return bytes(data)

    def save(self, output_path: str, sounds_dir: Optional[str] = None):
        """
        Save the project as a .ppak file.

        Args:
            output_path: Output .ppak file path
            sounds_dir: Directory containing .wav sound files (optional).
                        Files must be named "{NNN} {name}.wav" where NNN is a
                        zero-padded 3-digit sample number matching pad assignments
                        (e.g. "001 kick.wav", "042 snare.wav"). The device matches
                        pads to sounds by the numeric prefix.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as work_dir:
            # Create directory structure
            for group in ['a', 'b', 'c', 'd']:
                os.makedirs(os.path.join(work_dir, 'pads', group), exist_ok=True)
            os.makedirs(os.path.join(work_dir, 'patterns'), exist_ok=True)

            # Write pad files
            for group in ['a', 'b', 'c', 'd']:
                for pad in range(1, 13):
                    pad_path = os.path.join(work_dir, 'pads', group, f'p{pad:02d}')
                    with open(pad_path, 'wb') as f:
                        f.write(self._create_pad_data(group, pad))

            # Write pattern files
            for pattern_name, events in self.patterns.items():
                pattern_path = os.path.join(work_dir, 'patterns', pattern_name)
                with open(pattern_path, 'wb') as f:
                    f.write(self._create_pattern_data(events))

            # Write settings — always embed BPM as float32 LE at bytes 4-7.
            # All-zero settings causes "Error Clock" error on device.
            if self._template_settings:
                settings = bytearray(self._template_settings)
            else:
                settings = bytearray(222)
                # Bytes 24-215: 4 groups × 12 float32s (48 bytes each).
                # -1.0 is the device sentinel for "use default".
                # float[0] of each group is group project volume; default to 1.0.
                # All other positions default to -1.0.
                for i in range(48):  # 48 floats total (4 groups × 12)
                    struct.pack_into('<f', settings, 24 + i * 4, -1.0)
                for group_idx in range(4):
                    struct.pack_into('<f', settings, 24 + group_idx * 48, 1.0)
            struct.pack_into('<f', settings, 4, self.bpm)
            settings_path = os.path.join(work_dir, 'settings')
            with open(settings_path, 'wb') as f:
                f.write(bytes(settings))

            # Create tar
            tar_buffer = io.BytesIO()
            orig_dir = os.getcwd()
            os.chdir(work_dir)
            try:
                with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                    tar.add('pads')
                    tar.add('patterns')
                    tar.add('settings')
            finally:
                os.chdir(orig_dir)
            tar_data = tar_buffer.getvalue()

            # Create meta.json
            meta = {
                "info": "teenage engineering - pak file",
                "pak_version": 1,
                "pak_type": "project",
                "pak_release": "1.2.0",
                "device_name": "EP-133",
                "device_sku": self.device_sku,
                "device_version": "2.0.5",
                "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "author": "Claude",
                "base_sku": self.base_sku
            }

            # Create .ppak (ZIP with leading slashes)
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add tar
                info = zipfile.ZipInfo(f'/projects/P{self.project_num:02d}.tar')
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, tar_data)

                # Add meta.json
                info = zipfile.ZipInfo('/meta.json')
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, json.dumps(meta, indent=2))

                # Add sounds
                if sounds_dir and os.path.isdir(sounds_dir):
                    for fname in sorted(os.listdir(sounds_dir)):
                        if fname.lower().endswith('.wav'):
                            fpath = os.path.join(sounds_dir, fname)
                            with open(fpath, 'rb') as sf:
                                info = zipfile.ZipInfo(f'/sounds/{fname}')
                                info.compress_type = zipfile.ZIP_DEFLATED
                                zf.writestr(info, sf.read())

        return output_path


# Timing constants
TICKS_PER_BAR = 384
TICKS_PER_BEAT = 96
TICKS_PER_8TH = 48
TICKS_PER_16TH = 24
TICKS_PER_32ND = 12


def beat_to_ticks(beat: float) -> int:
    """Convert beat number (1-indexed) to ticks. Beat 1 = tick 0."""
    return int((beat - 1) * TICKS_PER_BEAT)


def create_basic_beat(project: EP133Project,
                      kick_pad: int = 10,
                      snare_pad: int = 7,
                      hihat_pad: int = 5):
    """Add a basic 4/4 beat to pattern a01"""
    # Kick on 1 and 3
    project.add_event('a01', 0, kick_pad, 127)
    project.add_event('a01', 192, kick_pad, 127)

    # Snare on 2 and 4
    project.add_event('a01', 96, snare_pad, 120)
    project.add_event('a01', 288, snare_pad, 120)

    # Hi-hats on 8th notes
    for i in range(8):
        vel = 90 if i % 2 == 0 else 70
        project.add_event('a01', i * 48, hihat_pad, vel)


if __name__ == '__main__':
    # Example usage
    project = EP133Project(bpm=120, device_sku="TE032AS001", project_num=1)

    # Assign samples — sound files must be named "{NNN} {name}.wav"
    project.assign_sample('a', 10, 1)    # pad 10 → "001 kick.wav"
    project.assign_sample('a', 7, 100)   # pad 7  → "100 snare.wav"
    project.assign_sample('a', 5, 200)   # pad 5  → "200 hihat.wav"

    # Create a basic beat
    create_basic_beat(project)

    # Save
    project.save('example_beat.ppak')
    print("Created example_beat.ppak")

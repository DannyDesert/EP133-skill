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


class EP133Project:
    """Create EP-133 project files (.ppak)"""

    def __init__(self, device_sku: str = "TE032AS001", project_num: int = 1):
        """
        Initialize a new EP-133 project.

        Args:
            device_sku: Device serial number (get from user's backup meta.json)
            project_num: Project slot 1-9
        """
        self.device_sku = device_sku
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
            time: Time position in ticks (0-383 for one bar)
            pad: Pad number 1-12
            velocity: Velocity 0-127 (default 100)
        """
        if pattern not in self.patterns:
            raise ValueError(f"Invalid pattern: {pattern}. Must be a01, b01, c01, or d01")
        if not 0 <= time <= 383:
            raise ValueError(f"Invalid time: {time}. Must be 0-383")
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

        events = sorted(events, key=lambda x: x[0])

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
            # Minimal 27-byte pad file
            data = bytearray(27)

        # Set sample number at bytes 1-2
        sample_num = self.pad_assignments[group].get(pad, 0)
        data[1:3] = struct.pack('<H', sample_num)

        return bytes(data)

    def save(self, output_path: str, sounds_dir: Optional[str] = None):
        """
        Save the project as a .ppak file.

        Args:
            output_path: Output .ppak file path
            sounds_dir: Directory containing .wav sound files (optional)
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

            # Write settings
            settings_path = os.path.join(work_dir, 'settings')
            if self._template_settings:
                with open(settings_path, 'wb') as f:
                    f.write(self._template_settings)
            else:
                # Minimal settings (222 bytes)
                with open(settings_path, 'wb') as f:
                    f.write(bytes(222))

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
                "pak_type": "user",
                "pak_release": "1.2.0",
                "device_name": "EP-133",
                "device_sku": self.device_sku,
                "device_version": "2.0.5",
                "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "author": "Claude",
                "base_sku": self.device_sku
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
    project = EP133Project(device_sku="TE032AS001", project_num=1)

    # Assign samples (example sample numbers)
    project.assign_sample('a', 10, 1)    # Kick
    project.assign_sample('a', 7, 100)   # Snare
    project.assign_sample('a', 5, 200)   # Hi-hat

    # Create a basic beat
    create_basic_beat(project)

    # Save
    project.save('example_beat.ppak')
    print("Created example_beat.ppak")

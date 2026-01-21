# Sample Beat Patterns

## Genre Templates

### Lo-Fi Hip Hop
```python
# Dusty, swung groove with ghost notes
def lofi_beat(project, kick=10, snare=7, hihat=5):
    # Swung kick pattern
    project.add_event('a01', 0, kick, 100)
    project.add_event('a01', 168, kick, 70)    # Ghost kick (swung)
    project.add_event('a01', 192, kick, 110)

    # Vinyl snare
    project.add_event('a01', 96, snare, 95)
    project.add_event('a01', 288, snare, 100)

    # Swung hi-hats
    swing_offset = 4
    for i in range(8):
        time = i * 48 + (swing_offset if i % 2 == 1 else 0)
        vel = 60 + (i % 2) * 20
        project.add_event('a01', time, hihat, vel)
```

### Phonk / Memphis
```python
# Hard hitting with cowbell
def phonk_beat(project, kick=10, snare=7, hihat=5, cowbell=4):
    # Double kicks
    project.add_event('a01', 0, kick, 127)
    project.add_event('a01', 72, kick, 100)
    project.add_event('a01', 144, kick, 127)
    project.add_event('a01', 192, kick, 127)
    project.add_event('a01', 264, kick, 95)
    project.add_event('a01', 336, kick, 120)

    # Hard snares
    project.add_event('a01', 96, snare, 127)
    project.add_event('a01', 288, snare, 127)

    # Rapid hi-hats (16ths)
    for i in range(16):
        vel = 100 if i % 4 == 0 else 70
        project.add_event('a01', i * 24, hihat, vel)

    # Cowbell on quarters
    for beat in [0, 96, 192, 288]:
        project.add_event('a01', beat, cowbell, 90)
```

### House (4-on-the-floor)
```python
def house_beat(project, kick=10, clap=12, hihat_closed=5, hihat_open=6):
    # Four-on-the-floor kick
    for beat in [0, 96, 192, 288]:
        project.add_event('a01', beat, kick, 127)

    # Clap on 2 and 4
    project.add_event('a01', 96, clap, 110)
    project.add_event('a01', 288, clap, 110)

    # Offbeat open hi-hats
    for beat in [48, 144, 240, 336]:
        project.add_event('a01', beat, hihat_open, 100)

    # 16th note closed hi-hats (lower velocity)
    for i in range(16):
        if i * 24 not in [48, 144, 240, 336]:  # Skip where open hats are
            project.add_event('a01', i * 24, hihat_closed, 50 + (i % 2) * 20)
```

### Trap
```python
def trap_beat(project, kick=10, snare=7, hihat=5, clap=12):
    # 808 kick pattern
    project.add_event('a01', 0, kick, 127)
    project.add_event('a01', 168, kick, 110)
    project.add_event('a01', 288, kick, 120)

    # Snappy snare with clap layer
    project.add_event('a01', 96, snare, 127)
    project.add_event('a01', 96, clap, 100)
    project.add_event('a01', 288, snare, 127)
    project.add_event('a01', 288, clap, 100)

    # 32nd note hi-hat rolls
    for i in range(32):
        vel = 100 - (i % 4) * 15  # Descending velocity pattern
        project.add_event('a01', i * 12, hihat, max(vel, 50))
```

### Boom Bap
```python
def boombap_beat(project, kick=10, snare=7, hihat=5, hihat_open=6):
    # Chunky kick with ghost
    project.add_event('a01', 0, kick, 120)
    project.add_event('a01', 144, kick, 85)   # Ghost
    project.add_event('a01', 192, kick, 115)
    project.add_event('a01', 336, kick, 90)   # Pickup

    # Fat snare
    project.add_event('a01', 96, snare, 127)
    project.add_event('a01', 288, snare, 120)

    # Simple hat pattern with open hat accent
    for i in range(8):
        if i == 5:  # Open hat on "and" of 3
            project.add_event('a01', i * 48, hihat_open, 90)
        else:
            vel = 80 if i % 2 == 0 else 55
            project.add_event('a01', i * 48, hihat, vel)
```

### Jungle / Drum & Bass
```python
def jungle_beat(project, kick=10, snare=7, hihat=5):
    # Chopped breakbeat style (meant for 160+ BPM)
    # This creates an amen-break style pattern

    events = [
        (0, kick, 127),      # KICK
        (24, hihat, 80),
        (48, snare, 120),    # snare
        (72, hihat, 70),
        (84, kick, 90),      # ghost kick
        (96, kick, 110),
        (108, hihat, 65),
        (120, snare, 100),
        (132, hihat, 75),
        (144, snare, 127),   # SNARE
        (156, kick, 85),
        (168, hihat, 80),
        (180, kick, 100),
        (192, snare, 115),
        (204, hihat, 70),
        (216, kick, 120),    # KICK
        (228, hihat, 60),
        (240, snare, 127),   # SNARE
        (252, kick, 80),
        (264, hihat, 75),
        (276, snare, 95),
        (288, kick, 115),
        (300, hihat, 70),
        (312, snare, 110),
        (324, hihat, 80),
        (336, kick, 100),
        (348, snare, 90),
        (360, hihat, 65),
        (372, kick, 85),
    ]

    for time, pad, vel in events:
        project.add_event('a01', time, pad, vel)
```

## Polyrhythmic Patterns

### 5 over 4
```python
def poly_5_over_4(project, pad=1):
    # 5 evenly spaced hits over one bar (384 ticks)
    spacing = 384 // 5  # 76.8 -> 77
    for i in range(5):
        project.add_event('a01', i * 77, pad, 100 - i * 10)
```

### 7 over 4
```python
def poly_7_over_4(project, pad=1):
    # 7 evenly spaced hits over one bar
    spacing = 384 // 7  # ~55
    for i in range(7):
        project.add_event('a01', i * 55, pad, 90)
```

## Fills and Variations

### Snare Roll
```python
def snare_roll(project, snare=7, start_time=288, duration=96):
    # 32nd note roll
    num_hits = duration // 12
    for i in range(num_hits):
        vel = 80 + int((i / num_hits) * 47)  # Crescendo
        project.add_event('a01', start_time + i * 12, snare, vel)
```

### Tom Fill
```python
def tom_fill(project, toms=[4, 3, 2, 1], start_time=288):
    # Descending tom fill
    for i, tom in enumerate(toms):
        project.add_event('a01', start_time + i * 24, tom, 120 - i * 10)
```

## Utility Functions

```python
def swing_time(time: int, amount: int = 8) -> int:
    """Apply swing to a time value. Offsets odd 8th notes."""
    eighth = time // 48
    remainder = time % 48
    if eighth % 2 == 1 and remainder == 0:
        return time + amount
    return time

def humanize(velocity: int, amount: int = 10) -> int:
    """Add random velocity variation"""
    import random
    return max(1, min(127, velocity + random.randint(-amount, amount)))
```

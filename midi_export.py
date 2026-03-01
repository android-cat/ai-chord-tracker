import mido
import re

# Map chord root names to MIDI note numbers (C4 = 60)
_NOTE_MAP = {
    'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68,
    'Ab': 68, 'A': 69, 'A#': 70, 'Bb': 70, 'B': 71
}

def _parse_chord(chord_str):
    """Parse a chord string into its root note and quality.
    
    Returns:
        tuple: (root_name, quality) or (None, None) for N.C.
    """
    if chord_str == "N.C." or chord_str == "---":
        return None, None
        
    # Match root note (e.g., C, C#, Db, F)
    match = re.match(r'^([A-G][#b]?)', chord_str)
    if not match:
        return None, None
        
    root = match.group(1)
    quality = chord_str[len(root):]
    return root, quality

def _get_chord_intervals(quality):
    """Return semitone intervals from the root for a given chord quality."""
    
    # Base triads
    if quality == "" or quality == "5": # Major / Power chord (simplify to Major for now or root+fifth)
        return [0, 4, 7] if quality == "" else [0, 7]
    elif quality == "m":
        return [0, 3, 7]
    elif quality == "dim":
        return [0, 3, 6]
    elif quality == "aug":
        return [0, 4, 8]
    elif quality == "sus4":
        return [0, 5, 7]
        
    # Sevenths
    elif quality == "7":
        return [0, 4, 7, 10]
    elif quality == "M7":
        return [0, 4, 7, 11]
    elif quality == "m7":
        return [0, 3, 7, 10]
    elif quality == "mM7":
        return [0, 3, 7, 11]
    elif quality == "dim7":
        return [0, 3, 6, 9]
    elif quality == "m7-5":
        return [0, 3, 6, 10]
    elif quality == "7-5":
        return [0, 4, 6, 10]
    elif quality == "M7-5":
        return [0, 4, 6, 11]
    elif quality == "aug7":
        return [0, 4, 8, 10]
    elif quality == "augM7":
        return [0, 4, 8, 11]
    elif quality == "7sus4":
        return [0, 5, 7, 10]
        
    # Sixths
    elif quality == "6":
        return [0, 4, 7, 9]
    elif quality == "m6":
        return [0, 3, 7, 9]
        
    # Added notes / Extensions (simplified for MIDI playback)
    elif "add9" in quality:
        if quality.startswith("m"): return [0, 3, 7, 14]
        return [0, 4, 7, 14]
    elif "69" in quality:
        if quality.startswith("m"): return [0, 3, 7, 9, 14]
        return [0, 4, 7, 9, 14]
        
    # Fallback: exact matches for complex extensions might be hard,
    # so we do simple string checks to provide a reasonable voicing.
    
    # 9ths
    if "(9)" in quality or "9" in quality:
        base = [0, 3, 7, 10] if quality.startswith("m") else [0, 4, 7, 10]
        if "M7" in quality: base[3] = 11
        base.append(14) # add 9th
        return base
        
    # Default fallback to major or minor based on first char
    if quality.startswith("m"):
        return [0, 3, 7]
    
    return [0, 4, 7]

def export_chords_to_midi(chord_timeline, filepath, bpm=120):
    """
    Export the chord timeline to a MIDI file.
    
    Args:
        chord_timeline: list of (start_sec, end_sec, chord_name)
        filepath: output .mid file path
        bpm: assumed tempo (default 120) for calculating ticks
    """
    try:
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        # Set tempo
        tempo = mido.bpm2tempo(bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
        
        ticks_per_beat = mid.ticks_per_beat
        
        def sec_to_ticks(sec):
            # ticks = (sec * ticks_per_beat * 1000000) / tempo
            return int((sec * ticks_per_beat * 1000000) / tempo)
            
        current_tick = 0
        
        for start_sec, end_sec, chord_str in chord_timeline:
            start_ticks = sec_to_ticks(start_sec)
            end_ticks = sec_to_ticks(end_sec)
            duration_ticks = end_ticks - start_ticks
            
            # If there's a gap before this chord, just wait
            if start_ticks > current_tick:
                delay = start_ticks - current_tick
            else:
                delay = 0
                
            root, quality = _parse_chord(chord_str)
            if not root or not root in _NOTE_MAP:
                # N.C. or unknown chord, just advance time without notes
                current_tick += duration_ticks + delay
                continue
                
            base_note = _NOTE_MAP[root]
            intervals = _get_chord_intervals(quality)
            
            notes = [base_note + interval for interval in intervals]
            
            # Note ON
            for i, note in enumerate(notes):
                # Only the first note in the chord applies the delay
                t = delay if i == 0 else 0
                track.append(mido.Message('note_on', note=note, velocity=64, time=t))
                
            # Note OFF
            for i, note in enumerate(notes):
                # The first note off happens after the duration
                t = duration_ticks if i == 0 else 0
                track.append(mido.Message('note_off', note=note, velocity=64, time=t))
                
            current_tick = end_ticks

        mid.save(filepath)
        return True, None
    except Exception as e:
        return False, str(e)

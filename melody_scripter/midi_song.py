import midi

from song_parser import Song, FileToParse, ParseException

import subprocess, os, re, sys

class MidiTrack(object):
    """A track in a song, also, the owner of one channel"""
    
    def __init__(self, midi_song, track, name, track_number, channel_number):
        self.midi_song = midi_song
        self.song = midi_song.song
        self.track = track
        self.track_number = track_number
        self.channel_number = channel_number
        self.id = "%s/%s" % (track_number, channel_number)
        self.name = name
        self.volume = track.volume
        self.midi_data = midi_song.midi_data
        self.midi_data_track = midi.Track()
        self.midi_data.append(self.midi_data_track)
        self.set_tempo_bpm(0, self.song.tempo_bpm)
        self.groove = self.song.groove
        self.set_instrument(0, self.track.instrument)
        self.initial_delay_subticks = midi_song.initial_delay_subticks
            
    def set_tempo_bpm(self, time, tempo):
        #print(" %s setting tempo at %s to %s bpm" % (self.id, time, tempo))
        self.midi_data_track.append(midi.SetTempoEvent(tick = time, bpm = tempo))
        
    def add_note(self, midi_note, time, duration):
        #print(" %s playing note %s at time %s, %s ticks" % (self.id, midi_note, time, duration))
        start_time = self.groove.get_subticks(time) + self.initial_delay_subticks
        self.midi_data_track.append(midi.NoteOnEvent(tick = start_time, channel = self.channel_number, 
                                                     pitch = midi_note, velocity = self.volume))
        end_time = self.groove.get_subticks(time+duration) + self.initial_delay_subticks
        self.midi_data_track.append(midi.NoteOffEvent(tick = end_time, channel = self.channel_number, 
                                                      pitch = midi_note))
        
    def add_notes(self, midi_notes, time, duration):
        #print(" %s playing notes %r at time %s, %s ticks" % (self.id, midi_notes, time, duration))
        start_time = self.groove.get_subticks(time) + self.initial_delay_subticks
        for midi_note in midi_notes:
            self.midi_data_track.append(midi.NoteOnEvent(tick = start_time, channel = self.channel_number, 
                                                         pitch = midi_note, velocity = self.volume))
        end_time = self.groove.get_subticks(time+duration) + self.initial_delay_subticks
        for midi_note in midi_notes:
            self.midi_data_track.append(midi.NoteOffEvent(tick = end_time, channel = self.channel_number, 
                                                          pitch = midi_note))
        
    def set_instrument(self, time, instrument_number):
        #print(" %s set instrument at %s to %s" % (self.id, time, instrument_number))
        self.midi_data_track.append(midi.ProgramChangeEvent(channel = self.channel_number, 
                                                            tick = time, value = instrument_number))

    def render(self):
        for item in self.track.items:
            item.visit_midi_track(self)
        self.midi_data_track.make_ticks_rel()
        self.midi_data_track.append(midi.EndOfTrackEvent(tick=1))
        
class MidiSong(object):
    
    def __init__(self, song, initial_delay_seconds = 0):

        self.song = song
        self.tempo_bpm = song.tempo_bpm
        self.groove = song.groove
        self.midi_tracks = {}
        self.initial_delay_subticks = int(round(initial_delay_seconds * song.subticks_per_second))

    def render(self):
        self.midi_data = midi.Pattern(resolution = self.song.ticks_per_beat * self.song.subticks_per_tick)
        
        for name, track in self.song.tracks.items():
            midi_track = self.add_midi_track(name, name, track)
            midi_track.render()
        # print self.midi_data
            
    def add_midi_track(self, key, name, track):
        next_track_number = len(self.midi_tracks)
        midi_track = MidiTrack(self, track, name, next_track_number, next_track_number)
        self.midi_tracks[key] = midi_track
        return midi_track

    def write_midi_file(self, file_name):
        #print("Rendering midi data...")
        self.render()
        print("Writing midi to %s ..." % file_name)
        midi.write_midifile(file_name, self.midi_data)
        
def play_midi_file_with_cvlc(file_name):
    print("Playing midi file %s with cvlc ..." % file_name)
    cvlc_path = '/usr/bin/cvlc'
    if os.path.exists(cvlc_path):
        subprocess.call([cvlc_path, file_name, 'vlc://quit'])
    else:
        print("Cannot play midi file, %s does not exist on your system" % cvlc_path)
    
def play_midi_file_with_timidity(file_name):
    subprocess.call(['/usr/bin/timidity', '--output-24bit', file_name])
    
def dump_midi_file(file_name):
    pattern = midi.read_midifile(file_name)
    return repr(pattern)
    
def compile_to_midi(song_file_path, midi_file_name, initial_delay_seconds = 0):
    song = Song.parse(FileToParse(song_file_path))
    midi_song = MidiSong(song, initial_delay_seconds = initial_delay_seconds)
    midi_song.write_midi_file(midi_file_name)
    

def play_song(song_file_path):
    midi_file_name = "%s.mid" % song_file_path
    print("Playing song %s (after compiling to %s) ..." % (song_file_path, midi_file_name))
    try:
        compile_to_midi(song_file_path, midi_file_name, initial_delay_seconds = 0.2)
        play_midi_file_with_cvlc(midi_file_name)
        #play_midi_file_with_timidity(midi_file_name)
#        dump_midi_file(midi_file_name)
    except ParseException, pe:
        pe.show_error()
    
def main():
    # Play a sample song
    song_file_name = 'canon_riff.song'
    song_file_path = os.path.join(os.path.dirname(__file__),'..', 'data', 'songs', song_file_name)
    play_song(song_file_path)

if __name__ == "__main__":
    main()

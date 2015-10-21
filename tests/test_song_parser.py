import unittest
from nose.tools import assert_raises
import regex

from melody_scripter import song_parser
from melody_scripter.song_parser import FileToParse, LineToParse, LineRegionToParse, ParseException, StringToParse
from melody_scripter.song_parser import Note, Rest, BarLine, Chord, SongItem, ScaleNote, SongItems, scale_note, Tie
from melody_scripter.song_parser import SongValuesCommand, SetSongTempoBpm, SetSongTimeSignature
from melody_scripter.song_parser import SetSongTicksPerBeat, SetSongSubTicksPerTick
from melody_scripter.song_parser import TrackValuesCommand, SetTrackInstrument, SetTrackVolume, SetTrackOctave
from melody_scripter.song_parser import SongCommand, Song, find_next_note, Scale, RelativeScale
from melody_scripter.song_parser import Groove, GrooveCommand

from contextlib import contextmanager

file_to_parse = FileToParse('name')

def as_region(string, left_offset = 12, right_offset = 15):
    full_text = '*' * left_offset + string + '#' * right_offset
    line_to_parse = LineToParse(file_to_parse, 1, full_text)
    return LineRegionToParse(line_to_parse, start = left_offset, end = left_offset + len(string))

class ParserTestCase(unittest.TestCase):
    @contextmanager
    def parse_exception(self, message, looking_at):
        try:
            yield
            self.fail('No ParseException')
        except ParseException, pe:
            self.assertEquals(pe.message, message)
            if pe.location is None:
                self.fail('ParseException %r has no location given' % pe.message)
            self.assertEquals(pe.location.rest_of_line()[0:len(looking_at)], looking_at)
            
    def assertEqualsDisplaying(self, x, y):
        if x != y:
            self.fail('Values not equal:\n  %r\n  %r' % (x, y))
            
class TestLineRegion(ParserTestCase):
    
    def test_stripped(self):
        region = as_region('   hello world  ')
        self.assertEquals(region.stripped().value, 'hello world')
        region = as_region('   hello world')
        self.assertEquals(region.stripped().value, 'hello world')
        region = as_region('hello world  ')
        self.assertEquals(region.stripped().value, 'hello world')
        
            
class TestNoteNames(ParserTestCase):
    
    def test_note_names(self):
        for letter, number in [('c', 0), ('d', 1), ('e', 2), ('f', 3), ('g', 4), ('a', 5), ('b', 6)]:
            self.assertEquals(song_parser.scale_number_from_letter(letter), number)
        for letter, number in [('C', 0), ('D', 1), ('E', 2), ('F', 3), ('G', 4), ('A', 5), ('B', 6)]:
            self.assertEquals(song_parser.scale_number_from_letter(letter), number)
            
    def test_note_name_strings(self):
        for i in range(7):
            self.assertEquals(song_parser.scale_number_from_letter(song_parser.NOTE_NAMES_LOWER_CASE[i]), i)
        for i in range(7):
            self.assertEquals(song_parser.scale_number_from_letter(song_parser.NOTE_NAMES_UPPER_CASE[i]), i)
            
class TestScaleNoteWithOctave(ParserTestCase):
    
    def test_parse_notes(self):
        self.assertEquals(scale_note('c0').midi_note, 12)
        self.assertEquals(scale_note('e0').note, 2)
        self.assertEquals(scale_note('e0').midi_note, 16)
        self.assertEquals(scale_note('f1').midi_note, 29)
        self.assertEquals(scale_note('f+1').midi_note, 30)
        self.assertEquals(scale_note('f+').semitone_offset, 6)
        self.assertEquals(scale_note('e').semitone_offset, 4)
        self.assertEquals(scale_note('f').semitone_offset, 5)
        self.assertEquals(scale_note('b').semitone_offset, 11)
        
        
class TestFindNextNote(ParserTestCase):
    
    def _verify_next_note(self, start_note, note, ups, result):
        self.assertEquals(find_next_note(scale_note(start_note).midi_note, 
                                         scale_note(note).semitone_offset, ups), 
                          scale_note(result).midi_note)
    
    def test_ups(self):
        self._verify_next_note('c3', 'c', 1, 'c4')
        self._verify_next_note('c3', 'd', 1, 'd3')
        self._verify_next_note('c3', 'a', 1, 'a3')
        self._verify_next_note('c3', 'a', 2, 'a4')
        self._verify_next_note('f3', 'd', 1, 'd4')
        self._verify_next_note('f3', 'g', 1, 'g3')
        self._verify_next_note('f3', 'f', 1, 'f4')
        
        
    def test_downs(self):
        self._verify_next_note('c3', 'c', -1, 'c2')
        self._verify_next_note('c3', 'd', -1, 'd2')
        self._verify_next_note('c3', 'a', -1, 'a2')
        self._verify_next_note('c3', 'a', -1, 'a2')
        self._verify_next_note('f3', 'd', -1, 'd3')
        self._verify_next_note('f3', 'g', -1, 'g2')
        self._verify_next_note('f3', 'f', -1, 'f2')
        
    def test_nearest(self):
        self._verify_next_note('c3', 'c', 0, 'c3')
        self._verify_next_note('c3', 'e', 0, 'e3')
        self._verify_next_note('c3', 'f', 0, 'f3')
        self._verify_next_note('c3', 'g', 0, 'g2')
        self._verify_next_note('f3', 'd', 0, 'd3')
        self._verify_next_note('f3', 'b-', 0, 'b-3')
        with assert_raises(ParseException) as pe:
            self._verify_next_note('f3', 'b', 0, 'b3')
        self.assertEquals(pe.exception.message, "Can't decide next nearest note (6 semitones either way)")
        
            
class TestSongParser(ParserTestCase):
    
    WORD_REGEX = regex.compile('[a-zA-Z]+')

    def test_script_line(self):
        left_offset = 9
        region = as_region('This is a line', left_offset = left_offset)
        self.assertEquals(region.pos, left_offset)
        word = region.parse(self.WORD_REGEX)
        self.assertEquals(word.value, 'This')
        self.assertEquals(region.pos, left_offset+4)
        
    def test_match(self):
        region = as_region('This is a line')
        test_regex = regex.compile(r'(?P<this>This)?|(?P<that>That)?')
        match = region.match(test_regex)
        group_dict = match.groupdict()
        self.assertEquals(group_dict['this'], 'This')
        self.assertEquals(group_dict['that'], None)
        
        
class TestNote(ParserTestCase):
    
    def test_note_equality(self):
        note1 = Note(0, 1, 1, (3, 4))
        self.assertEquals(note1, note1)
        self.assertEquals(note1, Note(0, 1, 1, (3, 4)))
        note1b = Note(0, 1, 1, (3, 4))
        note2 = Note(0, -1, 0, (1, 2))
        self.assertNotEquals(note1, note2)
        
    def test_note_unparse(self):
        note1 = Note(0, 1, 1, (3, 4))
        self.assertEquals(note1.unparse(), 'c+\'3q')
        note1 = Note(0, 1, -1, (3, 4))
        self.assertEquals(note1.unparse(), 'c+,3q')
        
    def test_note_parse(self):
        region = as_region('a+\'3q')
        note = Note.parse(region)
        self.assertEquals(note.source, region)
        self.assertEquals(note, Note(5, 1, 1, (3, 4)))
        self.assertEquals(note.semitone_offset, 10)
        region = as_region('a')
        note = Note.parse(region)
        self.assertEquals(note.source, region)
        self.assertEquals(note, Note(5))
        
        region = as_region('a+,3q')
        note = Note.parse(region)
        self.assertEquals(note, Note(5, 1, -1, (3, 4)))
        
    def test_parse_rest(self):
        region = as_region('r2.')
        rest = SongItem.parse(region)
        self.assertEquals(rest, Rest((6,2)))
        
    def test_parse_rest_no_duration(self):
        region = as_region('r')
        with self.parse_exception('Rest must specify duration', 'r'):
            rest = SongItem.parse(region)
        
    def test_note_parse_exception(self):
        with self.parse_exception('Invalid note: "a+\'3qmexico" (extra data "mexico")', 
                                  "mexico"):
            region = as_region('a+\'3qmexico')
            Note.parse(region)
        
class TestBarLine(ParserTestCase):
    def test_bar_equality(self):
        self.assertEquals(BarLine(), BarLine())
        
    def test_bar_line_unparse(self):
        self.assertEquals(BarLine().unparse(), '|')
        
    def test_bar_line_parse(self):
        region = as_region('|')
        bar_line = BarLine.parse(region)
        self.assertEquals(bar_line.source, region)
        self.assertEquals(bar_line, BarLine())
        
    def test_bar_line_parse(self):
        with self.parse_exception('Invalid bar line: "|extra" (extra data "extra")', 
                                  'extra'):
            region = as_region('|extra')
            BarLine.parse(region)
        
    def test_bar_line_parse_wrong(self):
        with self.parse_exception('Invalid bar line: "wrong"', 'wrong'):
            region = as_region('wrong')
            BarLine.parse(region)
        
    def test_bar_source_and_unparse(self):
        region = as_region('|')
        bar_line = BarLine.parse(region)
        self.assertEquals(bar_line.source.value, bar_line.unparse())
        
class TestTies(ParserTestCase):
    
    def test_tie_parse(self):
        region = as_region('~')
        tie = Tie.parse(region)
        self.assertEquals(tie.source, region)
        self.assertEquals(tie, Tie())
        
        
class TestChord(ParserTestCase):
    def test_chord_equality(self):
        chord1 = Chord(ScaleNote(0, 1), descriptor = 'maj7')
        chord2 = Chord(ScaleNote(0, 1), descriptor = 'maj7')
        self.assertEquals(chord1, chord2)
        chord3 = Chord(ScaleNote(0, 1), descriptor = 'm7')
        self.assertNotEquals(chord1, chord3)
        
    def test_chord_unparse(self):
        self.assertEquals(Chord(ScaleNote(0, 1), descriptor = 'm').unparse(), '[C+m]')
        self.assertEquals(Chord(ScaleNote(2), other_notes = [ScaleNote(4), ScaleNote(6)]).unparse(), '[:EGB]')

    def test_chord_parse_and_unparse(self):
        region = as_region('[:CE-G]')
        parsed_chord = Chord.parse(region)
        self.assertEquals(parsed_chord, Chord(ScaleNote(0), other_notes = [ScaleNote(2, -1), ScaleNote(4)]))
        self.assertEquals(parsed_chord.source.value, parsed_chord.unparse())
        region = as_region('[Cm7]')
        self.assertEquals(Chord.parse(region), Chord(ScaleNote(0), descriptor = 'm7'))
        
    def test_parse_chord_rest(self):
        region = as_region('[]')
        parsed_chord = Chord.parse(region)
        self.assertEquals(parsed_chord, Chord(None))
        
    def test_chord_with_bass(self):
        region = as_region('[:DFA]')
        parsed_chord = Chord.parse(region)
        parsed_chord.resolve(Song())
        self.assertEquals(parsed_chord.bass_midi_note, 14)
        
        region = as_region('[:DFA/C]')
        parsed_chord = Chord.parse(region)
        parsed_chord.resolve(Song())
        self.assertEquals(parsed_chord.bass_midi_note, 12)
        
    def test_chord_descriptor_midi_notes(self):
        region = as_region('[B]')
        parsed_chord = Chord.parse(region)
        parsed_chord.resolve(Song())
        self.assertEquals(parsed_chord.midi_notes, [35, 39, 42])

        region = as_region('[B-]')
        parsed_chord = Chord.parse(region)
        parsed_chord.resolve(Song())
        self.assertEquals(parsed_chord.midi_notes, [34, 38, 41])
        
    def test_chord_notes_midi_notes(self):
        region = as_region('[:CEG]')
        parsed_chord = Chord.parse(region)
        parsed_chord.resolve(Song())
        self.assertEquals(parsed_chord.midi_notes, [24, 28, 31])
        region = as_region('[:C+EG+]')
        parsed_chord = Chord.parse(region)
        parsed_chord.resolve(Song())
        self.assertEquals(parsed_chord.midi_notes, [25, 28, 32])
        

class TestSongItemParser(ParserTestCase):
    
    def test_parse_chord_song_item(self):
        region = as_region('[:CE-G]')
        parsed_item = SongItem.parse(region)
        self.assertEquals(parsed_item.source, region)
        region = as_region('[:CE-G]')
        parsed_chord = Chord.parse(region)
        self.assertEquals(parsed_item, parsed_chord)
        
    def test_parse_barline_song_item(self):
        region = as_region('|')
        parsed_item = SongItem.parse(region)
        region = as_region('|')
        parsed_barline = BarLine.parse(region)
        self.assertEquals(parsed_item, parsed_barline)
        
    def test_parse_tie_song_item(self):
        region = as_region('~')
        parsed_item = SongItem.parse(region)
        region = as_region('~')
        parsed_tie = Tie.parse(region)
        self.assertEquals(parsed_item, parsed_tie)
        
    def test_parse_note_song_item(self):
        region = as_region('a+\'3q')
        parsed_item = SongItem.parse(region)
        region = as_region('a+\'3q')
        parsed_note = Note.parse(region)
        self.assertEquals(parsed_item, parsed_note)
        
    def test_parse_tied_notes_song_item(self):
        region = as_region('~a+3q')
        parsed_item = SongItem.parse(region)
        self.assertEquals(parsed_item, Note(5, 1, duration = (3, 4), continued = True))
        region = as_region('a+3q~')
        parsed_item = SongItem.parse(region)
        self.assertEquals(parsed_item, Note(5, 1, duration = (3, 4), to_continue = True))
        region = as_region('~a+3q~')
        parsed_item = SongItem.parse(region)
        self.assertEquals(parsed_item, Note(5, 1, duration = (3, 4), to_continue = True, continued = True))
        
    def test_invalid_song_item(self):
        with self.parse_exception("Invalid song item: 'wrong'", 'wrong'):
            SongItem.parse(as_region('wrong'))
        
    def test_invalid_song_item_starts_like_note(self):
        with self.parse_exception('Invalid note: "a\'wrong" (extra data "wrong")', 'wrong'):
            SongItem.parse(as_region('a\'wrong'))
        
    def test_song_item_parse_regions(self):
        region = as_region(' [C] c e e c | [G] ')
        region.parse(SongItems.parse_regex)
        item_regions = region.named_groups('item')
        item_region_values = [region.value for region in item_regions]
        self.assertEquals(item_region_values, ['[C]', 'c', 'e', 'e', 'c', '|', '[G]'])

    def test_song_items(self):
        region = as_region(' [C] c e | [Am] ')
        song_items = list(SongItems.parse(region))
        expected_song_items = [Chord(ScaleNote(0), descriptor = ''), 
                               Note(0), Note(2), BarLine(), 
                               Chord(ScaleNote(5), descriptor = 'm')]
        self.assertEquals(song_items, expected_song_items)
        self.assertEquals(song_items[0].source.value, '[C]')
        self.assertEquals(song_items[3].source.value, '|')

class TestCommandParser(ParserTestCase):
    
    def test_int_value_parser(self):
        region = as_region('23')
        track_volume = SetTrackVolume.parse_value(region)
        self.assertEquals(track_volume, SetTrackVolume(23))
        with self.parse_exception('Invalid value for volume: 145 - must be an integer from 0 to 127', 
                                  '145'):
            SetTrackVolume.parse_value(as_region('145'))
        with self.parse_exception("Invalid value for volume: '12wrong' - must be an integer from 0 to 127", 
                                  '12wrong'):
            SetTrackVolume.parse_value(as_region('12wrong'))
        with self.parse_exception("Invalid value for volume: 'wrong' - must be an integer from 0 to 127", 
                                  'wrong'):
            SetTrackVolume.parse_value(as_region('wrong'))

            
    def test_value_setting_parser(self):
        region = as_region('tempo_bpm = 80')
        volume_setting = SongValuesCommand.parse_value_setting(region)
        self.assertEquals(volume_setting.source, region)
        self.assertEquals(volume_setting, SetSongTempoBpm(80))
        with self.parse_exception("Invalid value key for song: 'not_tempo_bpm'", 
                                  'not_tempo_bpm'):
            SongValuesCommand.parse_value_setting(as_region('not_tempo_bpm = 23'))
        with self.parse_exception('Invalid value for tempo_bpm: 23000 - must be an integer from 1 to 1000', 
                                  '23000'):
            SongValuesCommand.parse_value_setting(as_region('tempo_bpm = 23000'))
        
    def test_song_values_song_command(self):
        command_region = as_region('song: tempo_bpm=80, time_signature = 4/4 ,ticks_per_beat = 12 , subticks_per_tick = 5 ')
        
        values_command = SongCommand.parse(command_region)
        self.assertEquals(values_command.source, command_region)
        self.assertEquals(values_command, 
                          SongValuesCommand([SetSongTempoBpm(80), SetSongTimeSignature((4, 4)), 
                                             SetSongTicksPerBeat(12), SetSongSubTicksPerTick(5)]))
        
    def test_trailing_comma(self):
        command_region = as_region('song: tempo_bpm=80, time_signature = 4/4,  ')
        with self.parse_exception("Extra data when parsing: ',  '", ',  '):
            values_command = SongCommand.parse(command_region)

    def test_repeated_commas(self):
        command_region = as_region('song: tempo_bpm=80,, time_signature = 4/4,  ')
        with self.parse_exception("Extra data when parsing: ',, time_signature = 4/4,  '", ',, t'):
            values_command = SongCommand.parse(command_region)
        command_region = as_region('song: tempo_bpm=80, , time_signature = 4/4,  ')
        with self.parse_exception("Extra data when parsing: ', , time_signature = 4/4,  '", ', , t'):
            values_command = SongCommand.parse(command_region)

    def test_track_values_command(self):
        qualifier_region = as_region('melody')
        body_region = as_region('instrument = 73, volume=100, octave=3')
        values_command = TrackValuesCommand.parse_command(qualifier_region, body_region)
        self.assertEquals(values_command, 
                          TrackValuesCommand('melody', 
                                             [SetTrackInstrument(73), SetTrackVolume(100), SetTrackOctave(3)]))
        
class TestGroove(ParserTestCase):
    
    def test_groove(self):
        groove = Groove(beats_per_bar = 3, ticks_per_beat = 2, subticks_per_tick = 10,
                        delays = [0, 3])
        self.assertEquals(groove.get_subticks(tick = 0), 0)
        self.assertEquals(groove.get_subticks(tick = 1), 13)
        self.assertEquals(groove.get_subticks(tick = 2), 20)
        self.assertEquals(groove.get_subticks(tick = 20), 200)
        self.assertEquals(groove.get_subticks(tick = 23), 233)
        
    def test_parse_groove(self):
        region = as_region('groove: 0 3')
        command = SongCommand.parse(region)
        self.assertEquals(command, GrooveCommand(delays = [0, 3]))
        
        region = as_region('groove: 0 wrong 3')
        with self.parse_exception('Invalid groove delay: "wrong"', "wrong 3"):
            command = SongCommand.parse(region)
            
class TestTimeSignature(ParserTestCase):
    
    def test_parse_3_4(self):
        song_lines = "*song: time_signature = 3/4\n" + "c e | d e f | c"
        parse_string = StringToParse('test_string', song_lines)
        song = Song.parse(parse_string)
        
    def test_parse_3_8(self):
        song_lines = "*song: time_signature = 3/8\n" + "ch e | dh e f | ch"
        parse_string = StringToParse('test_string', song_lines)
        song = Song.parse(parse_string)
        
    def test_parse_2_2_ticks_error(self):
        song_lines = "*song: time_signature = 2/2, ticks_per_beat = 1\n" + " e | d e f g | d"
        parse_string = StringToParse('test_string', song_lines)
        with self.parse_exception('ticks per beat of 1 has to be a multiple of crotchets per beat of 2', 
                                  'ticks_per_beat'):
            song = Song.parse(parse_string)
            
class TestScaleDeclaration(ParserTestCase):
    
    def test_relative_scale(self):
        relative_scale = RelativeScale('major', [0, 2, 4, 5, 7, 9, 11])
        g_pos = relative_scale.get_position(7)
        self.assertEquals(g_pos, 4)
        high_f_pos = relative_scale.get_position(17)
        self.assertEquals(high_f_pos, 10)
        low_a_pos = relative_scale.get_position(-3)
        self.assertEquals(low_a_pos, -2)
        fsharp_pos = relative_scale.get_position(18)
        self.assertEquals(fsharp_pos, None)
    
    def test_parse_scale(self):
        region = as_region('D+3 minor')
        scale = Scale.parse(region)
        self.assertEquals(scale, Scale(ScaleNote(1, sharps = 1, octave = 3), 
                                       RelativeScale('minor', [0, 2, 3, 5, 7, 8, 10])))
    
    def test_parse_song_scale(self):
        song_lines = "*song: scale = C2 major\n*track.melody: octave = 2\n c e | d e f g | c, d'' "
        parse_string = StringToParse('test_string', song_lines)
        song = Song.parse(parse_string)
        self.assertEquals(song.scale, Scale(ScaleNote(0, octave = 2), 
                                            RelativeScale('major', [0, 2, 4, 5, 7, 9, 11])))
        note_items = [item for item in song.items if isinstance(item, Note)]
        scale_positions = [song.scale.get_position(note.midi_note) for note in note_items]
        self.assertEquals(scale_positions, [0, 2, 1, 2, 3, 4, 0, 8])
        
        
        
class TestSongParser(ParserTestCase):
    
    song_lines = """
*song:         tempo_bpm=120, ticks_per_beat=4
*track.chord:  octave = 2, instrument=40
*track.bass:   octave = 1, volume=90

[C] c e [:FAC] e ch ch | [G] g r2
"""
    def test_parse_song(self):
        parse_string = StringToParse('test_string', self.song_lines)
        song = Song.parse(parse_string)
        self.assertEqualsDisplaying(song, 
                                    Song([SongValuesCommand([SetSongTempoBpm(120), 
                                                             SetSongTicksPerBeat(4)]), 
                                          TrackValuesCommand('chord', 
                                                             [SetTrackOctave(2), SetTrackInstrument(40)]), 
                                          TrackValuesCommand('bass', 
                                                             [SetTrackOctave(1), SetTrackVolume(90)]), 
                                          Chord(ScaleNote(0), descriptor = ''), 
                                          Note(0, duration = (1, 1)), Note(2, duration = (1, 1)), 
                                          Chord(ScaleNote(3), other_notes = [ScaleNote(5), ScaleNote(0)]), 
                                          Note(2, duration = (1, 1)), 
                                          Note(0, duration = (1, 2)), 
                                          Note(0, duration = (1, 2)), 
                                          BarLine(), 
                                          Chord(ScaleNote(4), descriptor = ''), 
                                          Note(4, duration = (1, 1)), 
                                          Rest((2, 1))]))
        chord_track = song.tracks['chord']
        self.assertEquals(chord_track.instrument, 40)
        self.assertEquals(song.tracks['bass'].volume, 90)
        self.assertEquals(len(chord_track.items), 3)
        self.assertEquals(len(song.tracks['melody'].items), 6)
        
        self.assertEquals(chord_track.items[0].midi_notes, [36, 40, 43])
        self.assertEquals(chord_track.items[1].bass_midi_note, 29)
        
    def test_parse_song_cut(self):
        song_lines = """
            *song:         tempo_bpm=120, ticks_per_beat=4
                 | [C] c e 
                 [:FAC] e 
                 ! c | [G] r2
"""
        parse_string = StringToParse('test_string', song_lines)
        song = Song.parse(parse_string)
        self.assertEqualsDisplaying(song, 
                                    Song([SongValuesCommand([SetSongTempoBpm(120), 
                                                             SetSongTicksPerBeat(4)]),
                                          Note(0, duration = (1, 1)), 
                                          BarLine(), 
                                          Chord(ScaleNote(4), descriptor = ''), 
                                          Rest((2, 1))]))
        
    def test_subticks(self):
        song_lines = """
            *song:         tempo_bpm=120, ticks_per_beat=4, subticks_per_tick = 5
                 | [C] c 
"""
        parse_string = StringToParse('test_string', song_lines)
        song = Song.parse(parse_string)
        self.assertEqualsDisplaying(song, 
                                    Song([SongValuesCommand([SetSongTempoBpm(120), 
                                                             SetSongTicksPerBeat(4), 
                                                             SetSongSubTicksPerTick(5)]), 
                                          BarLine(), 
                                          Chord(ScaleNote(0), descriptor = ''), 
                                          Note(0, duration = (1, 1))
                                          ]))
    
    def _continuation_song(self, string):
        song_lines = "*song: ticks_per_beat=1, time_signature = 4/4\n%s" % string
        parse_string = StringToParse('test_string', song_lines)
        return Song.parse(parse_string)
        
    def _verify_durations(self, song_string, expected_note_durations):
        song = self._continuation_song(song_string)
        melody_track = song.tracks['melody']
        notes_to_verify = [item for item in melody_track.items if not item.continued]
        self.assertEquals([note.duration_ticks for note in notes_to_verify], expected_note_durations)
        
    def test_no_continuations(self):
        song = self._verify_durations('| a b b c | d e2 e1 |', [1, 1, 1, 1, 1, 2, 1])

    def test_invalid_continutations(self):
        with self.parse_exception('Tie appears after previous tie', '~ e1 |'):
            self._continuation_song('| a b b c | d e2 ~ ~ e1 |')
        with self.parse_exception('Note unnecessarily marked to continue after preceding tie', '~e1 |'):
            self._continuation_song('| a b b c | d e2 ~ ~e1 |')
        with self.parse_exception('Tie appears, but there is no previous note', '~ |'):
            self._continuation_song('~ | a b b c | d e2 e1 |')
        with self.parse_exception('Note marked as continued, but previous note not marked as to continue', '~b b c'):
            self._continuation_song('| a ~b b c | d e2 e1 |')
        with self.parse_exception('Note marked as continued, but there is no previous note', '~a b b'):
            self._continuation_song('| ~a b b c | d e2 e1 |')
        with self.parse_exception('Note not marked as continued, but previous note was marked as to continue', 'b c |'):
            self._continuation_song('| b~ ~b~ b c | d e2 e1 |')
        with self.parse_exception('Continued note is not the same pitch as previous note', '~b b c'):
            self._continuation_song('| a~ ~b b c | d e2 e1 |')
        with self.parse_exception('Continued note is not the same pitch as previous note', 'b b c'):
            self._continuation_song('| a ~ b b c | d e2 e1 |')
        with self.parse_exception('Continued note is not the same pitch as previous note', '~d e2'):
            self._continuation_song('| a b b c~ | ~d e2 e1 |')
        
    def test_valid_continutations(self):
        song = self._verify_durations('| b ~ b b c | c e2 e1 |', [2, 1, 1, 1, 2, 1])
        song = self._verify_durations('| b~ ~b b c | c e2 e1 |', [2, 1, 1, 1, 2, 1])
        song = self._verify_durations('| b~ ~b ~ b c | c e2 e1 |', [3, 1, 1, 2, 1])
        song = self._verify_durations('| b~ ~b~ ~b c | c e2 e1 |', [3, 1, 1, 2, 1])
        song = self._verify_durations('| b b b c~ | ~c e2 e1 |', [1, 1, 1, 2, 2, 1])
        song = self._verify_durations('| b ~ b b c | c e2 ~ e1 |', [2, 1, 1, 1, 3])
        song = self._verify_durations('| b ~ b b c | ~ c e2~ ~e1 |', [2, 1, 2, 3])
    
    def test_note_too_high(self):
        song_lines = """*track.melody: octave = 5\n c c' c' c' | c' d d' e'"""
        parse_string = StringToParse('test_string', song_lines)
        with self.parse_exception('Note number 134 > 127', "d' e'"):
            song = Song.parse(parse_string)
        
    def test_note_too_low(self):
        song_lines = """*track.melody: octave = 4\n c c, c, c, | c, d, e, f, """
        parse_string = StringToParse('test_string', song_lines)
        with self.parse_exception('Note number -8 < 0', "e, f, "):
            song = Song.parse(parse_string)
            
class MidiTrackVisitor(object):
    def __init__(self, transpose):
        self.transpose = transpose
        self.midi_notes = []
        
    def add_note(self, note, tick, duration):
        self.midi_notes.append(note)
        
    def add_notes(self, notes, tick, duration):
        self.midi_notes.append(notes)
    
class TestTransposition(ParserTestCase):
    
    def test_invalid_transpose_value(self):
        song_lines = ("*song: transpose = 310\nc c")
        parse_string = StringToParse('test_string', song_lines)
        with self.parse_exception('Invalid value for transpose: 310 - must be an integer from -127 to 127', 
                                  '310'):
            song = Song.parse(parse_string)
            
    def test_transpose_out_of_range(self):
        song_lines = ("*song: transpose = 0\n*track.melody: octave = 8\n c")
        parse_string = StringToParse('test_string', song_lines)
        song = Song.parse(parse_string)
        song_lines = ("*song: transpose = 100\n*track.melody: octave = 8\n c")
        parse_string = StringToParse('test_string', song_lines)
        song = Song.parse(parse_string)
        track_visitor = MidiTrackVisitor(transpose = song.transpose)
        note_items = [item for item in song.items if isinstance(item, Note)]
        with self.parse_exception('Note number 208 > 127', 'c'):
            for note in note_items:
                note.visit_midi_track(track_visitor)
    
    def test_transpose(self):
        song_lines = ("*song: transpose = 3\n*track.melody: octave = 2\n*track.chord: octave = 1\n*track.bass:octave = 0\n" + 
                      "c c [C]")
        parse_string = StringToParse('test_string', song_lines)
        song = Song.parse(parse_string)
        note_items = [item for item in song.items if isinstance(item, Note)]
        first_note = note_items[0]
        self.assertEquals(first_note.midi_note, 36)
        track_visitor = MidiTrackVisitor(transpose = song.transpose)
        first_note.visit_midi_track(track_visitor)
        self.assertEquals(track_visitor.midi_notes[0], 39)
        chord_items = [item for item in song.items if isinstance(item, Chord)]
        first_chord = chord_items[0]
        self.assertEquals(first_chord.midi_notes, [24, 28, 31])
        first_chord.visit_midi_track(track_visitor)
        self.assertEquals(track_visitor.midi_notes[1], [27, 31, 34])
        self.assertEquals(first_chord.bass_midi_note, 12)
        bass_note = song.tracks['bass'].items[0]
        bass_note.visit_midi_track(track_visitor)
        self.assertEquals(track_visitor.midi_notes[2], 15)

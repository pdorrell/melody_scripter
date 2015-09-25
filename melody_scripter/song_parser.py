import subprocess, os, regex, sys

DIATONIC_OFFSETS = [0, 2, 4, 5, 7, 9, 11]

CHORD_DESCRIPTOR_OFFSETS = {'': [0, 4, 7], 
                            '7': [0, 4, 7, 10], 
                            'm': [0, 3, 7], 
                            'm7': [0, 3, 7, 10], 
                            'maj7': [0, 4, 7, 11]}

NOTE_NAMES_LOWER_CASE = "cdefgab"

NOTE_NAMES_UPPER_CASE = "CDEFGAB"

DEFAULT_DURATION = (1, 1)

def scale_number_from_letter(letter):
    ord_letter = ord(letter)
    if ord_letter > 96:
        offset_from_c = ord(letter) - 99
    else:
        offset_from_c = ord(letter) - 67
    return offset_from_c if offset_from_c >= 0 else offset_from_c + 7

def valid_midi_note(midi_note):
    if midi_note < 0:
        raise ParseException('Note number %s < 0' % midi_note)
    if midi_note > 127:
        raise ParseException('Note number %s > 127' % midi_note)
    return midi_note

class ParseException(Exception):
    def __init__(self, message, location, location_pos = False):
        super(Exception, self).__init__(message)
        if location_pos:
            self.location = location.remaining()
        else:
            self.location = location
        
    def show_error(self):
        self.location.show_error(self.message)
        
class ParseLeftOverException(Exception):
    def __init__(self, leftover):
        super(Exception, self).__init__('Extra data when parsing: %r' % leftover)
        self.leftover = leftover

class FileToParse(object):
    def __init__(self, file_name):
        self.file_name = file_name
        
    def read_lines(self):
        line_number = 0
        with open(self.file_name, "r") as f:
            for line in f.readlines():
                line = line.rstrip('\n')
                line_number += 1
                yield LineToParse(self, line_number, line).as_region()
                
class StringToParse(object):
    def __init__(self, file_name, lines_string):
        self.file_name = file_name
        self.lines = lines_string.split("\n")
    
    def read_lines(self):
        line_number = 0
        for line in self.lines:
            line_number += 1
            yield LineToParse(self, line_number, line).as_region()

                
class LineToParse(object):
    def __init__(self, file_to_parse, line_number, line):
        self.file_to_parse = file_to_parse
        self.line_number = line_number
        self.line = line
        
    def as_region(self):
        return LineRegionToParse(self, 0, len(self.line), self.line)
        
    def show_error(self, error_message, pos):
        print("")
        print("%s:%s:%s" % (self.file_to_parse.file_name, self.line_number, error_message))
        print("")
        print(self.line)
        indent = " " * pos
        print("%s^" % indent)
        print("%s%s" % (indent, error_message))
        print("")

        
class LineRegionToParse(object):
    def __init__(self, line_to_parse, start, end, value, regex = None, match = None):
        self.line_to_parse = line_to_parse
        self.start = start
        self.end = end
        self.value = value
        self.pos = self.start
        self.regex = regex
        self.matched = match
        self.matched_groupdict = match.groupdict() if match else None
        
    def parse(self, regex, completely = False):
        match = regex.match(self.line_to_parse.line, self.pos, self.end)
        if match:
            self.pos = match.end()
            if completely and self.pos < self.end:
                raise ParseLeftOverException(self.line_to_parse.line[self.pos:self.end])
            return LineRegionToParse(self.line_to_parse, match.start(), match.end(), match.group(), regex, match)
        else:
            return None
        
    def rest_of_line(self):
        return self.line_to_parse.line[self.start:]
        
    def sub_region(self, span):
        start, end = span
        return LineRegionToParse(self.line_to_parse, start, end, self.line_to_parse.line[start:end])
        
    def match(self, regex):
        match = regex.match(self.line_to_parse.line, self.pos, self.end)
        return match
    
    def remaining(self):
        return LineRegionToParse(self.line_to_parse, self.pos, self.end, self.line_to_parse.line[self.pos:self.end])
        
    def named_group(self, name):
        if self.match and self.matched_groupdict[name] is not None:
            group_index = self.regex.groupindex[name]
            return LineRegionToParse(self.line_to_parse, self.matched.start(group_index), self.matched.end(group_index), self.matched.group(group_index))
        else:
            return None
        
    def show_error(self, error_message):
        self.line_to_parse.show_error(error_message, self.start)
        
class Parseable(object):
    
    def __eq__(self, other):
        return (other is not None and self.__class__ == other.__class__ and self.as_data() == other.as_data())
    
    def __ne__(self, other):
        return not (self == other)
    
    def __hash__(self):
        return hash(self.__class__) + hash(self.as_data())
    
    def __repr__(self):
        return "%s:%r" %  (self.__class__.__name__, self.as_data())

    @classmethod
    def parse(cls, region):
        try:
            parsed = region.parse(cls.parse_regex, completely = True)
        except ParseLeftOverException, pleo:
            raise ParseException('Invalid %s: %r (extra data %r)' 
                                 % (cls.description, region.value, pleo.leftover), 
                                 region, location_pos = True)
        if parsed:
            parsed_instance = cls.parse_from_group_dict(parsed.matched_groupdict, parsed)
            parsed_instance.source = region
            return parsed_instance
        else:
            raise ParseException('Invalid %s: %r' % (cls.description, region.value), region)

class Cut(Parseable):
    description = 'cut'
    parse_regex = regex.compile(r'[!]')

    @classmethod
    def parse_from_group_dict(cls, group_dict, source):
        return Cut()
        
    def unparse(self):
        return '!'
    
class Tie(Parseable):
    description = 'tie'
    parse_regex = regex.compile(r'[~]')

    cuttable = True

    @classmethod
    def parse_from_group_dict(cls, group_dict, source):
        return Tie()
        
    def unparse(self):
        return '~'
    
    def as_data(self):
        return {}
    
    def resolve(self, song):
        if song.awaiting_tie:
            raise ParseException('Tie appears after previous tie', self.source)
        if song.last_note:
            if song.last_note.to_continue:
                raise ParseException('Tie appears, but last note already marked to continue', self.source)
            song.last_note.to_continue = True
        else:
            raise ParseException('Tie appears, but there is no previous note', self.source)
        song.awaiting_tie = True

class BarLine(Parseable):

    description = 'bar line'
    parse_regex = regex.compile(r'[|]')
    
    cuttable = True
    
    def resolve(self, song):
        song.playing = True
        if song.last_bar_tick is None:
            part_bar_ticks = song.tick
            if part_bar_ticks > song.ticks_per_bar:
                raise ParseException('First partial bar is %s ticks long > %s ticks per bar' *
                                     (part_bar_ticks, song.ticks_per_bar), self.source)
        else:
            bar_ticks = song.tick - song.last_bar_tick
            if bar_ticks != song.ticks_per_bar:
                raise ParseException("Completed bar is %s ticks long, but expected %s ticks" %
                                     (bar_ticks, song.ticks_per_bar), self.source)
        song.last_bar_tick = song.tick
        song.current_duration = DEFAULT_DURATION
    
    @classmethod
    def parse_from_group_dict(cls, group_dict, source):
        return BarLine()
        
    def unparse(self):
        return '|'
    
    def as_data(self):
        return {}
    
def scale_note(string):
    return ScaleNote.parse_with_octave(string)
    
class ScaleNote(Parseable):
    def __init__(self, note, sharps = 0, upper_case = True):
        self.note = note
        self.sharps = sharps
        self.upper_case = upper_case
        self.semitone_offset = DIATONIC_OFFSETS[self.note] + self.sharps
        
    parse_with_octave_regex = regex.compile('^(?P<letter>[a-g])(?P<sharp_or_flat>[+-]?)(?P<octave>[0-9])?$')
        
    @classmethod
    def parse_with_octave(self, string):
        match = self.parse_with_octave_regex.match(string)
        if match:
            groupdict = match.groupdict()
            sharps_string = groupdict['sharp_or_flat']
            if sharps_string == '+':
                sharps = 1
            elif sharps_string == '-':
                sharps = -1
            else:
                sharps = 0
            scale_note = ScaleNote(scale_number_from_letter(groupdict['letter']), 
                                   sharps, upper_case = False)
            octave_string = groupdict['octave']
            if octave_string:
                scale_note.set_octave(int(octave_string))
            return scale_note
        else:
            raise ParseException('Invalid scale note with octave: %r' % string, None)
        
    def set_octave(self, octave):
        self.octave = octave
        self.midi_note = valid_midi_note(12 + self.octave*12 + self.semitone_offset)
        
    def set_upward_from(self, note):
        semitones_up = (144 + self.semitone_offset - note.midi_note) % 12
        self.midi_note = valid_midi_note(note.midi_note + semitones_up)
        
    def as_data(self):
        return dict(note=self.note, sharps=self.sharps, upper_case=self.upper_case)
        
    def unparse(self):
        letter_string = (NOTE_NAMES_UPPER_CASE if self.upper_case else NOTE_NAMES_LOWER_CASE)[self.note]
        sharps_string = "+" * self.sharps if self.sharps > 0 else "-" * -self.sharps
        return letter_string + sharps_string
    
class Chord(Parseable):
    
    cuttable = True
    
    def __init__(self, root_note, other_notes = None, descriptor = None, bass_note = None):
        self.root_note = root_note
        self.other_notes = other_notes
        self.descriptor = descriptor
        self.bass_note = bass_note
            
    def get_midi_notes(self):
        if self.descriptor is not None:
            offsets = CHORD_DESCRIPTOR_OFFSETS[self.descriptor]
            return [valid_midi_note(self.root_note.midi_note + offset) for offset in offsets]
        else:
            return [valid_midi_note(note.midi_note) for note in [self.root_note] + self.other_notes]
        
    def get_bass_midi_note(self, bass_octave):
        bass_note = self.bass_note or self.root_note
        return valid_midi_note(12 + bass_octave*12 + bass_note.semitone_offset) if bass_note else None
    
    CHORD_NOTES_MATCHER = r'(:(?P<chord_notes>([A-G][+-]?)+))'
    ROOT_MATCHER = r'(?P<chord_root>[A-G]([+-]?))'
    DESCRIPTOR_MATCHER = r'(?P<chord_descriptor>7|m|m7|maj7|)'
    BASS_MATCHER = r'(/(?P<bass>[A-G][+-]?))'
            
    CHORD_MATCHER = r'\[(((%s|%s%s)%s?)|)\]' % (CHORD_NOTES_MATCHER, ROOT_MATCHER, DESCRIPTOR_MATCHER, BASS_MATCHER)
    parse_regex = regex.compile(CHORD_MATCHER)
    
    def resolve(self, song):
        song.playing = True
        if song.last_chord:
            song.last_chord.finish(song)
        self.tick = song.tick
        chord_track = song.tracks['chord']
        chord_octave = chord_track.octave
        if self.root_note is None:
            self.midi_notes = []
        else:
            self.root_note.set_octave(chord_octave)
            if self.other_notes:
                last_note = self.root_note
                for note in self.other_notes:
                    note.set_upward_from(last_note)
                    last_note = note
            self.midi_notes = self.get_midi_notes()
        song.last_chord = self
        chord_track.add(self)
        bass_track = song.tracks['bass']
        bass_octave = bass_track.octave
        self.bass_midi_note = self.get_bass_midi_note(bass_octave)
        
    def visit_midi_track(self, midi_track):
        midi_track.add_notes(self.midi_notes, self.tick, self.duration_ticks)
        
    def finish(self, song):
        self.duration_ticks = song.tick - self.tick
        if self.bass_midi_note:
            bass_track_note = BassNote(self.bass_midi_note, self.tick, self.duration_ticks)
            bass_track = song.tracks['bass']
            bass_track.add(bass_track_note)
    
    def as_data(self):
        return dict(root_note=self.root_note, other_notes=self.other_notes, 
                    descriptor=self.descriptor, bass_note = self.bass_note)
        
    def unparse(self):
        if self.descriptor:
            return "[%s%s]" % (self.root_note.unparse(), self.descriptor)
        else:
            return "[:%s%s]" % (self.root_note.unparse(), "".join([note.unparse() for note in self.other_notes]))
        
    description = 'chord'
        
    @classmethod
    def get_chord_notes_from_string(cls, chord_notes_string):
        notes = []
        for char in chord_notes_string:
            if char in ['-', '+']:
                notes[-1].sharps = 1 if char == '+' else -1
            else:
                notes.append(ScaleNote(scale_number_from_letter(char)))
        return notes
    
    @classmethod
    def parse_one_note(cls, note_string):
        if note_string:
            return cls.get_chord_notes_from_string(note_string)[0]
        else:
            return None
        
    @classmethod
    def parse_from_group_dict(cls, group_dict, source):
        chord_notes_string = group_dict['chord_notes']
        bass_note_string = group_dict['bass']
        bass_note = cls.parse_one_note(bass_note_string)
        if chord_notes_string:
            notes = cls.get_chord_notes_from_string(chord_notes_string)
            return Chord(notes[0], other_notes = notes[1:], bass_note = bass_note)
        else:
            root_note_string = group_dict['chord_root']
            root_note = cls.parse_one_note(root_note_string)
            descriptor = group_dict['chord_descriptor']
            return Chord(root_note, descriptor = descriptor, bass_note = bass_note)
        

def resolve_duration(note_or_rest, song):
    x, y = note_or_rest.duration
    if song.ticks_per_beat % y != 0:
        raise ParseException('Duration %d/%d is not compatible with ticks per beat of %d' %
                             (x, y, song.ticks_per_beat))
    note_or_rest.duration_ticks = x * (song.ticks_per_beat/y)
    song.tick += note_or_rest.duration_ticks
    
class Rest(Parseable):
    def __init__(self, duration):
        self.duration = duration
        self.cuttable = True
        
    def as_data(self):
        return self.duration

    def resolve(self, song):
        song.playing = True
        self.tick = song.tick
        resolve_duration(self, song)
        
def find_next_note(last_note, offset, ups, location = None):
    last_note_offset = last_note % 12
    if last_note_offset == offset:
        return last_note + 12 * ups
    else:
        last_note_from_just_below = last_note_offset if last_note_offset < offset else last_note_offset-12
        jump_up_from_below = offset - last_note_from_just_below
        this_note_above_last_note = last_note + jump_up_from_below
        if ups == 0:
            if jump_up_from_below < 6:
                return this_note_above_last_note
            elif jump_up_from_below > 6:
                return this_note_above_last_note - 12
            else:
                raise ParseException("Can't decide next nearest note (6 semitones either way)", location)
        elif ups > 0:
            return this_note_above_last_note + (ups-1) * 12
        elif ups < 0:
            return this_note_above_last_note + ups*12
        

class BassNote(object):
    
    def __init__(self, midi_note, tick, duration_ticks):
        self.midi_note = midi_note
        self.tick = tick
        self.duration_ticks = duration_ticks

    def visit_midi_track(self, midi_track):
        midi_track.add_note(self.midi_note, self.tick, self.duration_ticks)

class Note(Parseable):
    
    cuttable = True
    
    def __init__(self, note, sharps = 0, ups = 0, duration = None, 
                 to_continue = False, continued = False):
        self.ups = ups
        self.note = note
        self.sharps = sharps
        self.duration = duration
        self.to_continue = to_continue
        self.continued = continued
        self.semitone_offset = DIATONIC_OFFSETS[self.note] + self.sharps
        self.continuation_start = self
        
    def resolve(self, song):
        song.playing = True
        self.tick = song.tick
        if self.duration is None:
            self.duration = song.current_duration
        melody_track = song.tracks['melody']
        if song.last_note:
            self.resolve_from_last_note(song.last_note)
        else:
            self.octave = melody_track.octave
            self.midi_note = valid_midi_note(12 + self.octave*12 + self.semitone_offset)
        resolve_duration(self, song)
        song.current_duration = self.duration
        melody_track.add(self)
        self.resolve_continuation(song)
        song.last_note = self
        
    def resolve_continuation(self, song):
        if song.awaiting_tie:
            if self.continued:
                raise ParseException('Note unnecessarily marked to continue after preceding tie', 
                                     self.source)
            self.continued = True
            song.awaiting_tie = False
        if self.continued:
            if song.last_note:
                if not song.last_note.to_continue:
                    raise ParseException('Note marked as continued, but previous note not marked as to continue', 
                                         self.source)
                if self.midi_note != song.last_note.midi_note:
                    raise ParseException('Continued note is not the same pitch as previous note', self.source)
                self.continuation_start = song.last_note.continuation_start
                self.continuation_start.duration_ticks += self.duration_ticks
            else:
                raise ParseException('Note marked as continued, but there is no previous note', self.source)            
        
    def visit_midi_track(self, midi_track):
        if not self.continued:
            midi_track.add_note(self.midi_note, self.tick, self.duration_ticks)
        
    def resolve_from_last_note(self, last_note):
        self.midi_note = valid_midi_note(find_next_note(last_note.midi_note, self.semitone_offset, self.ups, location = self.source))
        
    CONTINUED_MATCHER = r'(?P<continued>[~])?'
    UPS_OR_DOWNS_MATCHER = r'((?P<ups>\^+)|(?P<downs>V+)|)'
    NOTE_NAME_MATCHER = r'(?P<note>[a-g][+-]?)'
    REST_MATCHER = r'(?P<rest>r)'
    DURATION_MATCHER = r'(?P<beats>[1-9][0-9]*)?(?P<hqs>[hq]+)?(?P<triplet>t)?(?P<dot>[.])?'
    TO_CONTINUE_MATCHER = r'(?P<to_continue>[~])?'
    NOTE_COMMAND_MATCHER = '%s%s(%s|%s)%s%s' % (CONTINUED_MATCHER, UPS_OR_DOWNS_MATCHER, REST_MATCHER, 
                                                NOTE_NAME_MATCHER, DURATION_MATCHER, TO_CONTINUE_MATCHER)
    parse_regex = regex.compile(NOTE_COMMAND_MATCHER)
    
    def as_data(self):
        return dict(ups = self.ups, note = self.note, 
                    sharps = self.sharps, duration = self.duration, 
                    continued = self.continued, to_continue = self.to_continue)
    
    description = 'note'
    
    @classmethod
    def parse_from_group_dict(cls, group_dict, source):
        ups = len(group_dict['ups'] or '')
        downs = len(group_dict['downs'] or '')
        ups = ups - downs
        if group_dict['rest']:
            note = None
        else:
            note_string = group_dict['note']
            note = scale_number_from_letter(note_string[0])
            if len(note_string) == 2:
                if note_string[1] == '+':
                    sharps = 1
                else:
                    sharps = -1
            else:
                sharps = 0
        duration_found = False
        x = 1
        y = 1
        if group_dict['beats']:
            x = x*int(group_dict['beats'])
            duration_found = True
        if group_dict['hqs']:
            for ch in group_dict['hqs']:
                if ch == 'h':
                    y = y*2
                if ch == 'q':
                    y = y*4
                duration_found = True
        if group_dict['triplet']:
            y = y*3
            duration_found = True
        if group_dict['dot']:
            x = x*3
            y = y*2
            duration_found = True
        if duration_found:
            duration = (x, y)
        else:
            duration = None
        to_continue = group_dict['to_continue'] == '~'
        continued = group_dict['continued'] == '~'
        if note is None:
            if duration is None:
                raise ParseException('Rest must specify duration', source)
            return Rest(duration)
        else:
            return Note(note, sharps, ups, duration, to_continue = to_continue, continued = continued)
        
    def unparse(self):
        ups_string = "^" * self.ups if self.ups > 0 else "V" * -self.ups
        letter_string = "r" if self.note is None else NOTE_NAMES_LOWER_CASE[self.note]
        sharps_string = "+" * self.sharps if self.sharps > 0 else "-" * -self.sharps
        x, y = self.duration
        duration_string = "" if x == 1 else str(x)
        while y > 1:
            old_y = y

            if y%4 == 0:
                duration_string += "q"
                y = y/4
            elif y%3 == 0:
                duration_string += "t"
                y = y/3
            elif y%2 == 0:
                duration_string += "h"
                y = y/2
            if y == old_y and y > 1:
                raise Exception("Can't notate duration quotient %s" % y)
        return ups_string + letter_string + sharps_string + duration_string
    
class ParseFromChoices(object):

    @classmethod
    def parse(self, region):
        match = region.match(self.choice_regex)
        if match:
            group_dict = match.groupdict()
            group_dict_items = [(k,v) for k, v in group_dict.items() if v is not None]
            if len(group_dict_items) == 1:
                key, value = group_dict_items[0]
                return self.class_dict[key].parse(region)
            elif len(group_dict) == 0:
                raise Exception('Parse regex matched, but didn\'t match any items in class dict')
            else:
                raise Exception('Ambiguous regex, parse result = %r' % group_dict)
        else:
            raise ParseException('Invalid %s: %r' % (self.description, region.value), region)

        
class SongItem(ParseFromChoices):
    
    description = 'song item'
    
    choice_regex = regex.compile(r'(?P<chord>[[])|(?P<barline>[|])|(?P<note>[~]?[Va-gr^])|(?P<tie>[~])|(?P<cut>[!])')
    
    class_dict = dict(chord = Chord, barline = BarLine, note = Note, cut = Cut, tie = Tie)


class ParseItems(object):
    
    @classmethod
    def parse_item_regions(cls, region):
        match = region.match(cls.items_regex)
        if match:
            item_group_index = cls.items_regex.groupindex['item']
            item_capture_spans = match.spans(item_group_index)
            return [region.sub_region(span) for span in item_capture_spans]
        
    @classmethod
    def parse(cls, region):
        item_regions = cls.parse_item_regions(region)
        return [cls.item_class.parse(item_region) for item_region in item_regions]    


class SongItems(ParseItems):
    
    items_regex = regex.compile(r'\s*((?P<item>\S+)\s*)*')
    
    item_class = SongItem


class IntValueParser(object):
    
    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value
        
    def raise_invalid_value_exception(self, label, value, value_region):
        raise ParseException('Invalid value for %s: %r - must be an integer from %s to %s' %
                             (label, value, self.min_value, self.max_value), 
                             value_region)
        
    def parse(self, label, value_region):
        value_string = value_region.value
        try:
            value = int(value_string)
        except ValueError:
            self.raise_invalid_value_exception(label, value_string, value_region)
        if value < self.min_value or value > self.max_value:
            self.raise_invalid_value_exception(label, value, value_region)
        return value

class ValueSetter(Parseable):
    
    def __init__(self, value):
        self.value = value
        
    def as_data(self):
        return self.value
        
    @classmethod
    def parse(cls, region):
        value = cls.value_parser.parse(cls.key, region)
        value_setter = cls(value)
        return value_setter
    
class ValuesCommand(Parseable):
    
    VALUE_SETTING_REGEX = regex.compile(r'((?P<key>[^=\s]+)\s*=\s*(?P<value>.*))')
    
    def __init__(self, values):
        self.values = values
        self.cuttable = False
        
    def as_data(self):
        return self.values
    
    @classmethod
    def parse_value_setting(cls, region):
        parsed = region.parse(cls.VALUE_SETTING_REGEX, completely = True)
        key_region = parsed.named_group('key')
        value_region = parsed.named_group('value')
        key = key_region.value
        value_setter_class = cls.value_setters.get(key)
        if value_setter_class is None:
            raise ParseException('Invalid value key for %s: %r' % (cls.description, key), 
                                 key_region)
        value_setting = value_setter_class.parse(value_region)
        value_setting.source = region
        return value_setting
    
    @classmethod
    def parse(cls, region):
        match = region.match(cls.parse_regex)
        if match:
            item_group_index = cls.parse_regex.groupindex['item']
            item_capture_spans = match.spans(item_group_index)
            item_regions = [region.sub_region(span) for span in item_capture_spans]
            values = [cls.parse_value_setting(item_region) for item_region in item_regions]
            init_args = cls.get_init_args(values, match)
            values_command = cls(*init_args)
            values_command.source = region
            return values_command
        
    
class SetSongTempoBpm(ValueSetter):
    key = 'tempo_bpm'
    value_parser = IntValueParser(1, 1000)
    
    def resolve(self, song):
        song.unplayed().tempo_bpm = self.value
    
class SetSongBeatsPerBar(ValueSetter):
    key = 'beats_per_bar', 
    value_parser = IntValueParser(1, 32)
    
    def resolve(self, song):
        song.unplayed().set_beats_per_bar(self.value)
    
class SetSongTicksPerBeat(ValueSetter):
    key = 'ticks_per_beat'
    value_parser = IntValueParser(1, 2000)
    
    def resolve(self, song):
        song.unplayed().set_ticks_per_beat(self.value)
    
class SongValuesCommand(ValuesCommand):
    
    description = 'song'

    value_setters = dict(tempo_bpm = SetSongTempoBpm, 
                         beats_per_bar = SetSongBeatsPerBar, 
                         ticks_per_beat = SetSongTicksPerBeat)
    
    parse_regex = regex.compile(r'song:\s*(\s*(?P<item>[^,]+)\s*[,]?)*')

    @classmethod
    def get_init_args(cls, values, match):
        return [values]
    
    def resolve(self, song):
        for value in self.values:
            value.resolve(song)
    

class SetTrackInstrument(ValueSetter):
    key = 'instrument'
    value_parser = IntValueParser(0, 127)
    
    def resolve(self, track):
        track.unplayed().instrument = self.value
    
class SetTrackVolume(ValueSetter):
    key = 'volume'
    value_parser = IntValueParser(0, 127)
    
    def resolve(self, track):
        track.unplayed().volume = self.value

class SetTrackOctave(ValueSetter):
    key = 'octave'
    value_parser = IntValueParser(-1, 10)
    
    def resolve(self, track):
        track.unplayed().octave = self.value
    
class TrackValuesCommand(ValuesCommand):
    
    description = 'track'
    
    def __init__(self, name, values):
        super(TrackValuesCommand, self).__init__(values)
        self.name = name
    
    def as_data(self):
        return (self.name, self.values)
    
    value_setters = dict(instrument = SetTrackInstrument, 
                         volume = SetTrackVolume, 
                         octave = SetTrackOctave)

    parse_regex = regex.compile(r'track.(?P<name>[a-z]+):\s*(\s*(?P<item>[^,]+)\s*[,]?)*')

    @classmethod
    def get_init_args(cls, values, match):
        name = match.groupdict()['name']
        return [name, values]

    def resolve(self, song):
        track = song.tracks.get(self.name)
        if track is None:
            raise ParseException('Unknown track: %r' % self.name)
        for value in self.values:
            value.resolve(track)

class NamedCommand(object):
    @classmethod
    def parse(cls, region):
        match = region.match(cls.command_regex)
        if match:
            group_dict = match.groupdict()
            command = group_dict['command']
            command_class = cls.commands.get(command)
            if command_class is None:
                raise ParseException('Unknown %s: %r' % (cls.description, command), 
                                     region)
            return command_class.parse(region)
        else:
            raise ParseException('Invalid %s' % cls.description, region)

    
class SongCommand(NamedCommand):
    
    command_regex = regex.compile(r'(?P<command>[^.:]+)(.[^:]+)?:')
    
    description = 'song command'
    
    commands = dict(song = SongValuesCommand, 
                    track = TrackValuesCommand)
    
class Track(object):
    
    def __init__(self, song, octave = 3):
        self.song = song
        self.octave = octave
        self.volume = 100
        self.instrument = 0
        self.items = []
        
    def clear_items(self):
        self.items = []
        
    def unplayed(self):
        self.song.unplayed()
        return self
    
    def add(self, item):
        self.items.append(item)

class Song(Parseable):
    
    LINE_REGEX = regex.compile('\s*([*](?P<command>.*)|(?P<song_items>.*))')
    
    def __init__(self, items = None):
        self.items = [] if items is None else items[:]
        
        self.beats_per_bar = 4
        self.ticks_per_beat = 4
        self.recalculate_tick_values()
        self.playing = False # some command can only happen before it starts playing
        self.tempo_bpm = 120
        self.set_to_start()
        self.tracks = dict(melody = Track(self, octave = 3), chord = Track(self, octave = 1), 
                           bass = Track(self, octave = 0))
        
    def clear_items(self):
        self.items = [item for item in self.items if not item.cuttable]
        self.set_to_start()
        for track in self.tracks.values():
            track.clear_items()
        
    def set_to_start(self):
        self.last_bar_tick = None
        self.tick = 0 # current time in ticks
        self.last_note = None
        self.current_duration = DEFAULT_DURATION
        self.last_chord = None
        self.last_bar_tick = None
        self.awaiting_tie = False
        
    @property
    def ticks_per_second(self):
        ticks_per_minute = self.tempo_bpm * self.ticks_per_beat
        return ticks_per_minute/60.0
        
    def set_ticks_per_beat(self, ticks_per_beat):
        self.ticks_per_beat = ticks_per_beat
        self.recalculate_tick_values()
        
    def recalculate_tick_values(self):
        self.ticks_per_bar = self.beats_per_bar * self.ticks_per_beat
        
    def set_beats_per_bar(self, beats_per_bar):
        self.beats_per_bar = beats_per_bar
        self.recalculate_tick_values()
        
    def unplayed(self):
        if self.playing:
            raise ParseException('Cannot perform operation once song is playing')
        return self
        
    def as_data(self):
        return self.items
        
    def add(self, item):
        if item.__class__ == Cut:
            self.clear_items()
        else:
            item.resolve(self)
            self.items.append(item)
        
    def check_last_part_bar(self):
        part_bar_ticks = self.tick if self.last_bar_tick is None else self.tick - self.last_bar_tick
        if part_bar_ticks > self.ticks_per_bar:
            raise ParseException('Last part bar has %s ticks > %s ticks per bar' % (part_bar_ticks, self.ticks_per_bar))
            
    def finish(self):
        self.check_last_part_bar()
        if self.last_chord:
            self.last_chord.finish(self)

    @classmethod
    def parse(cls, parse_file):
        song = Song()
        for line in parse_file.read_lines():
            for item in cls.parse_line(line):
                song.add(item)
        song.finish()
        return song
        
    @classmethod
    def parse_line(cls, line):
        parsed = line.parse(cls.LINE_REGEX)
        command_line = parsed.named_group('command')
        if command_line:
            return [SongCommand.parse(command_line)]
        else:
            song_items = parsed.named_group('song_items')
            if song_items:
                return SongItems.parse(song_items)
            else:
                raise Exception('No match for line: %r' % parsed.value)
        
            
    def __repr__(self):
        return 'Song[%s]' % (", ".join(["%r" % item for item in self.items]))
    

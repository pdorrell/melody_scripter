import unittest
import os

from melody_scripter import song_parser
from melody_scripter.midi_song import compile_to_midi, dump_midi_file

class RegressionTests(unittest.TestCase):
    
    def setUp(self):
        this_dir = os.path.dirname(__file__)
        self.songs_dir = os.path.abspath(os.path.join(this_dir, '..', 'data', 'songs'))
        self.output_dir = os.path.join(this_dir, 'regression', 'output')
        if not os.path.isdir(self.output_dir): os.makedirs(self.output_dir)
        self.expected_files_dir = os.path.join(this_dir, 'regression', 'expected')
        if not os.path.isdir(self.expected_files_dir): os.makedirs(self.expected_files_dir)
        
    def _read_binary_file(self, file_name):
        with open(file_name, mode = "rb") as f:
            return f.read()
        
    def _dump_midi_file(self, midi_file_name, dump_file_name):
        dump_string = dump_midi_file(midi_file_name)
        with open(dump_file_name, mode = "w") as f:
            f.write(dump_string)
        
    def _test_song_regression(self, file_name):
        song_file_name = os.path.join(self.songs_dir, file_name)
        expected_midi_file_name = os.path.join(self.expected_files_dir, file_name + ".mid")
        expected_midi_dump_file_name = expected_midi_file_name + ".dump"
        output_midi_file_name = os.path.join(self.output_dir, file_name + ".mid")
        output_midi_dump_file_name = output_midi_file_name + ".dump"
        if os.path.isfile(output_midi_file_name):
            os.remove(output_midi_file_name)
        compile_to_midi(song_file_name, output_midi_file_name)
        self._dump_midi_file(output_midi_file_name, output_midi_dump_file_name)
        output_midi = self._read_binary_file(output_midi_file_name)
        if os.path.isfile(expected_midi_file_name):
            expected_midi = self._read_binary_file(expected_midi_file_name)
            self._dump_midi_file(expected_midi_file_name, expected_midi_dump_file_name)
            if output_midi != expected_midi:
                self.fail('Midi file %s is different to expected %s' % (output_midi_file_name, expected_midi_file_name))
        else:
            self.fail('Expected midi file %s does not exist (to compare with %s)' % (expected_midi_file_name, output_midi_file_name))

        
    def test_song_regressions(self):
        print("")
        for file_name in os.listdir(self.songs_dir):
            if file_name.endswith('.song'):
                print(" regression test on song %s ..." % file_name)
                self._test_song_regression(file_name)

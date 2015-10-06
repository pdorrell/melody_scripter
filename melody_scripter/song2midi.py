import sys

from midi_song import compile_to_midi

def main():
    if len(sys.argv) == 2:
        song_file_path = sys.argv[1]
        midi_file_path = "%s.mid" % song_file_path
        print("Compiling song file %s to %s ..." % (song_file_path, midi_file_path))
        compile_to_midi(song_file_path, midi_file_path, initial_delay_seconds = 0.2)
        print("Successfully wrote midi file %s." % midi_file_path)
    else:
        print("Useage: %s <song_file_name>" % sys.argv[0])

if __name__ == "__main__":
    main()

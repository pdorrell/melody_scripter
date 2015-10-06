import sys

from midi_song import play_song

def main():
    if len(sys.argv) == 2:
        song_file_path = sys.argv[1]
        play_song(song_file_path)
    else:
        print("Useage: %s <song_file_name>" % sys.argv[0])

if __name__ == "__main__":
    main()

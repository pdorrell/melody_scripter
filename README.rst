Melody Scripter
===============

*Melody Scripter* is an Python application which parses melody files written
in an easy-to-write textual format into an internal Python object model.

For the purposes of *Melody Scripter*, a "melody" consists of a sequence
of notes on the standard Western musical scale, together with bar lines
(which must match the specified time signature) and chords, with optional
bass notes where different from the chord root note.

The internal object model can generate a Midi file for the melody.
A header file allows Midi properties to be specified, including:

* Tempo in BPM

* Beats per bar

* Ticks per bar

* For each of the melody track, chord track and bass track:

  * Midi instrument number

  * Volume ('velocity')

  * Octave for first note of the melody, all chord root notes, and all bass notes
    (the melody format avoids the need to specify octave values for any melody
    note other than the first).

(Currently Midi output is the only functionality provided by the object model,
but it is intended as a convenient representation of melody information
for the purposes of scientific analysis.)


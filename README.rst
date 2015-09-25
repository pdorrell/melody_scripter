Melody Scripter
===============

**Melody Scripter** is a Python application which parses melody files written
in an easy-to-write textual format into an internal Python object model.

For the purposes of **Melody Scripter**, a "melody" consists of a sequence
of notes on the standard Western musical scale, together with bar lines
(which must match the specified time signature) and chords, with optional
bass notes where different from the chord root note.

The internal object model can generate a Midi file for the melody.

Currently Midi output is the only functionality provided by the object model,
but it is also intended as a convenient representation of melody information
for the purposes of scientific analysis.

Melody Scripter File Format
===========================

The Melody Script file format is line-oriented. Currently there are two types
of input lines:

* **Command lines**. Any line starting with the character '*' (with possibly
  preceding whitespace) is parsed as a command line.
* **Song Item** lines. All other lines are parsed as sequences of whitespace-separated Song Items.

Command Lines
-------------

A command line starts with a **command** (after the initial '*' character).

The command is followed by a ':' character, and then one or more
comma separated arguments.

Currently there are four commands, which are **song**, and three 'track' commands:
**track.melody**, **track.chord** and **track.bass**.

All four commands take arguments which are **property settings**, consisting 
in each case of a **key** and a **value**.

Currently all property settings can be executed only prior to any song items,
but in future they may be allowed during the song (or additional commands may
be defined which are valid within the song).

Song Property Settings
----------------------

Available property settings for the **song** command are:

+----------------+--------------------------------------+------------+--------------+
| key            | value                                | default    | valid values |
+================+======================================+============+==============+
| tempo_bpm      | Tempo in beats per minute            | 120        | 1 to 1000    |
+----------------+--------------------------------------+------------+--------------+
| beats_per_bar  | Beats per bar                        | 4          | 1 to 32      |
+----------------+--------------------------------------+------------+--------------+
| ticks_per_beat | Ticks per beat                       | 4          | 1 to 2000    |
+----------------+--------------------------------------+------------+--------------+


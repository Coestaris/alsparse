# ALSParse

Simple parser for ALS (Ableton Live Set) files.
Supports:
- project metadata;
- audio/midi/return/group/main tracks;
- audio clips (start, end, name, color);
- midi clips (start, end, name, color, notes);
- automation (parameter name as a barely-human-readable string, value, time);

Additionally there's some tools for working with ALS files:
- `tools/dump.py` - dumps all the data from ALS file;
- `tools/visualize/viz.py` - generates a video visualization of ALS file (as a rolling piano roll);

Visit these tools for more information.

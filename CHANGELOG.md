# Changelog

Process notes for this project: what I did in what order, problems found and re-runs.
The README holds only the current findings.

## 2026-11-14 and 15

Set up the repo and the data, and checked that viewer IDs link across videos.

- The dataset page links one zip (181 MB, 1.7 GB unpacked). It holds head-tracking
  logs only. The 18 videos are separate downloads and I leave them until the demo.
- The authors publish no checksum. `scripts/download.py` pins the SHA-256 I got, so
  a changed file fails loudly.
- Layout: two experiments, 48 viewer folders each, nine session files per folder,
  one demographics file for both experiments. 864 sessions in all.
- Format facts I checked before designing anything:
  - Rows arrive about every 11 ms (roughly 90 a second).
  - Each row has a wall-clock timestamp and the video's playback time. In some
    files the first few rows still carry the previous video's playback time before
    it drops to zero. Parsing will have to cut those rows.
  - The orientation is a unit quaternion in Unity's left-handed axes (x right, y up,
    z forward). The paper gives the formula for the forward direction.
  - The picture is wrapped starting from the +x axis, so the middle of the frame is
    behind the direction the headset calls forward. The paper says the wrap is
    "anti-clockwise" but not seen from where, so left and right in the frame are
    ambiguous until I can compare with video frames in the demo step. Coverage
    numbers do not depend on it, because the tile grid is the same mirrored.
- Viewer IDs (`results/id_linkage.md`):
  - Within an experiment a folder is one person. 94 of 96 folders are a single
    sitting of nine videos in play order, about 45 minutes long, and no two folders
    were ever recorded at the same time. The two exceptions each have one video
    recorded again on a later day.
  - Across the experiments the paper speaks of 48 participants and ships one
    demographics file, but never states outright that folder numbers match. The
    recordings support it without proving it: seated headset height correlates
    0.37 between the experiments (permutation p = 0.005), against 0.97 to 0.99
    between halves of one sitting.
  - Because the across-experiment link rests partly on trust, results that carry a
    viewer's style from one experiment to the other will also be shown with
    same-experiment videos only.
- Related work is in `docs/related_work.md`. I could read 360BroadView and CUB360
  only at abstract level, and the note says so.

Parsing, tiles, field of view and heatmaps.

- Every viewer is put on the video's own playback clock at 10 samples a second
  (`src/parse.py`). Leftover rows from the previous video, backward jitter and the
  frozen tail after the video ends are cut. A sample with no recorded row within a
  quarter of a second is marked missing. Missing data is at most 1.3% in any video
  (`results/data_summary.md`).
- `src/geometry.py` turns an orientation into the share of the viewer's window in
  each of 6 x 12 tiles. The window is 100 x 100 degrees and turns with the head,
  tilt included. I sample it with a 20 x 20 grid of rays on the flat screen, so a
  share means share of what is on screen.
- Mistake caught by a test: with a 21 x 21 grid the middle ray sat exactly on a
  tile edge whenever the viewer faced a tile corner, and rounding sent the whole
  middle row to one side. An even grid has no middle ray.
- Wrong guess of mine, also caught by a test: I expected the four tiles around the
  view centre to hold most of the window. They hold about a quarter. A 100 degree
  window touches 16 tiles even when perfectly lined up.
- The heatmaps (`results/heatmaps/`) put the hot spot of every experiment 2 video
  in the middle of the frame, which is where the paper says the stage or pitch is.
  That agrees with the axis convention I took from the paper.
- The two experiments differ a lot. In experiment 2 the 16 most-watched tiles take
  82% of all viewing on average, against 61% in experiment 1, and heads move about
  half as fast. So experiment 2 is the easy case for any crowd method.

Baselines: own motion, random crowds and a blend.

- Set-up choices, made before looking at chosen groups:
  - The stream is cut into one-second segments. A horizon of h seconds means the
    tiles for a segment are picked h seconds before it starts.
  - Budget: 16 of 72 tiles. Rule: the smallest budget at which perfect foresight
    covers at least 95% of the window (`results/budget.md`).
  - Each trial splits the 48 viewers into 16 test viewers and a pool of 32. Groups
    come from the pool only. The first version of my design scored "everyone not
    in the group", but then a method that puts unusual viewers in the group would
    also remove them from the test set and look better for free.
  - "Own motion" means "assume the viewer keeps looking where they look now". I did
    not add velocity extrapolation. The TRACK paper found the plain version hard to
    beat, and my question is about the crowd.
  - A crowd's score does not depend on the horizon, because earlier viewers' whole
    traces are known. Only own motion and the blend change with the horizon.
  - Blend weight: picked per group size and horizon on the other 17 videos, with
    separate random splits from the evaluation.
- Results (`results/baselines.md`, `results/crowd_curve.png`):
  - Own motion covers 86.8% at 1 second, 81.9% at 2 and 74.9% at 5.
  - A random crowd covers 66.9% with one viewer and 77.4% with 32. Most of the gain
    is in by 8 viewers (75.8%).
  - So a crowd alone only beats own motion at 5 seconds, and only from about 8
    viewers up. At 1 second the blend adds half a point at best. At 5 seconds the
    blend with 32 viewers adds about 5 points over own motion.
  - Intervals over videos are wide for the crowd (about 6 points each way), because
    videos differ so much. Comparisons between arms will be paired by video.
- Speed: the first version of tile picking spent most of its time rolling arrays to
  find neighbours. A fixed 72 x 72 neighbour matrix made a trial about 2.6 times
  faster, and videos now run in parallel processes with their own seeds.

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

Viewing styles, and chosen groups against random groups.

- Three style numbers per viewer and video: head speed, exploration (entropy of
  tiles visited) and share of the window on the 16 tiles the other viewers watch
  most. Each is a z-score within the video. A viewer's style for a test video is
  the average over the other videos.
- Checked before any outcome (`results/style_check.md`): style is a stable trait.
  Head speed correlates 0.88 between two halves of the videos, exploration 0.80,
  time on the crowd 0.62. Across the two experiments the figures are 0.51, 0.36
  and 0.29, which also supports the viewer numbers matching across experiments.
  The three numbers are strongly related (head speed and exploration 0.80), so in
  practice there is one main axis, from calm to active.
- Three ways of picking k viewers from the pool, written down before the run:
  random; mixed (k-means into k style clusters, one viewer nearest each centre);
  typical (the k viewers most on the crowd), added as a control so that a gain
  from "choosing" could be told apart from a gain from variety.
- Result (`results/chosen_vs_random.md`): the mixed group is not better than a
  random group of the same size. At 4 viewers it is 0.3 points lower on average
  coverage (-0.6 to +0.0) and 0.3 lower for the worst-served 10% (-0.5 to -0.0).
  The typical group is 1.3 points higher at 4 viewers (+0.8 to +1.9) and 2.4
  higher at one viewer. All differences shrink to nothing by 16 viewers. With
  the blend of own motion and crowd, every difference is under 0.6 points.
- The same comparison with style from same-experiment videos only gives the same
  picture (mixed -0.7 at 4 viewers, typical +1.4).
- Two checks on why (`results/why_not_mixed.md`):
  - Budget. I thought the mixed group might fail only because 16 tiles is about
    one window, leaving no room to serve a second camp. At 24 tiles the mixed
    group is still 0.2 points below random at 4 viewers.
  - Who predicts whom. Active viewers are not predicted better by other active
    viewers. A group of four active viewers covers 71.6% of an active viewer's
    window, against 72.2% from four calm viewers. Own kind minus the others is
    -0.8 points for active viewers (-1.4 to -0.2).
- What I take from it: style here says how a person watches, not where they will
  look. Two explorers do not explore the same place, so putting an explorer in
  the group buys nothing for the next explorer and spends tiles away from the
  main action.
- Runtime: the main run took about 45 minutes on nine processes. The longest
  video (11 minutes) sets the pace because videos run one per process.

Four chosen viewers against sixteen random ones.

- `scripts/four_vs_sixteen.py` reads the per-video table from the previous step, so
  the comparison is paired on the same splits and test viewers.
- Result (`results/four_vs_sixteen.md`): sixteen random viewers beat four chosen
  ones in every version. Crowd only, four mixed viewers are 3.4 points below
  sixteen random (-4.0 to -2.8) and lose in all 18 videos. Four typical viewers
  are 1.8 points below (-2.3 to -1.3). With the blend at 2 seconds the gaps are
  about half a point, still in favour of sixteen.
- Read off the random curve, four mixed viewers are worth 3.8 random viewers and
  four typical viewers are worth 6.4.
- So the answer to the project's question is no on both counts. Quantity explains
  most of what a crowd gives. Who is in the crowd matters a little when the crowd
  is very small, and then it pays to pick conformists.
- The verdict words in the table come from the intervals. I wrote the three
  possible sentences into the code before the result existed and let the numbers
  pick one.

Demo clip, and a correction to how the frame is drawn.

- Which way round the picture runs. I had read the paper's "wrapped anti-clockwise"
  one way and noted that I could not be sure without video frames. For the demo I
  downloaded one video and drew every viewer's view centre on a real frame under
  both readings (`results/frame_orientation.jpg`). My first reading puts the gaze
  cluster on empty backdrop. The mirrored reading puts it on the performer. So the
  picture is mirrored relative to the angle I use in the code.
- What this changes: only drawings. The heatmaps in `results/heatmaps/` were
  redrawn so that left and right match the real video. No coverage number moves,
  because a mirrored tile grid is the same grid, and there is a test for that.
- The demo (`results/demo.gif`, `results/demo.md`) shows one viewer's real head
  motion over ten seconds of the first video, twice: with the 16 tiles picked from
  4 viewers mixed by style, and from 16 random viewers. Both groups are the ones
  that trial used in the results. Tiles outside the 16 are drawn blocky.
- How I picked the clip, so nobody takes it for evidence: I used the one video I
  had downloaded, took the viewer whose gap between the two groups over the whole
  video was closest to that video's average gap, and then the ten seconds where
  that viewer's gap was largest. In the clip the two groups cover 59% and 90% of
  the window. Over the whole video they cover 75% and 80% for this viewer.
- The dataset's video files are 16:9 although the content is a full sphere, so
  the demo rescales frames to 2:1 before cutting out the window.
- The first GIF was 11 MB. Keeping five frames a second and 64 colours brought it
  to 4.9 MB.

README and notebook.

- `scripts/check_readme.py` pulls every number out of the README and looks for it in
  the generated notes under `results/`. The list is in `results/readme_numbers.md`.
  Three numbers are settings or facts and are listed as such in the script: 2017,
  360 and 100. A test runs the same check and the README's style rules.
- The first draft of the README was 1,243 words. I cut it to under 1,200.
- The notebook in `notebooks/` runs the pipeline with 20 trials per video and writes
  to `results_quick/`, so it never overwrites the files the README cites.

# Chosen groups against random groups of the same size

Written by `scripts/chosen_vs_random.py`. Budget 16 of 72 tiles, 200 trials per video, 18 held-out
videos. In each trial the three arms pick k viewers from the same pool of 32 and are scored on
the same 16 test viewers. Style comes from the other 17 videos.

## Levels: crowd only, coverage %

| k | random, average | random, worst 10% | mixed, average | mixed, worst 10% | typical, average | typical, worst 10% |
|---|---|---|---|---|---|---|
| 1 | 66.9 | 53.8 | 67.0 | 53.3 | 69.3 | 55.7 |
| 2 | 70.2 | 57.3 | 69.7 | 56.9 | 72.0 | 58.4 |
| 4 | 73.8 | 59.4 | 73.5 | 59.2 | 75.1 | 60.0 |
| 8 | 75.8 | 60.5 | 75.5 | 60.5 | 76.4 | 60.7 |
| 16 | 76.9 | 61.0 | 76.8 | 60.9 | 77.1 | 60.9 |
| 32 | 77.4 | 61.1 | 77.4 | 61.1 | 77.4 | 61.1 |

## Differences from random at the same k

Each cell is the mean difference over videos, its 95% bootstrap interval over videos, and the
number of videos in which the arm beat random. Coverage is in percentage points, where above
zero is better. Poor seconds are per minute, where below zero is better. At k = 32 the group is
the whole pool, so every arm is the same and the row is left out.

### Crowd only

| k | Arm | Coverage, average viewer | Coverage, worst 10% | Poor seconds per minute, worst 10% |
|---|---|---|---|---|
| 1 | mixed | +0.2 (-2.1 to +2.2), 11/18 | -0.4 (-2.3 to +1.2), 11/18 | +0.3 (-0.9 to +1.6), 6/18 |
| 1 | typical | +2.4 (+0.6 to +3.9), 15/18 | +2.0 (+1.1 to +2.9), 14/18 | -1.6 (-2.1 to -1.0), 2/18 |
| 2 | mixed | -0.5 (-1.3 to +0.4), 7/18 | -0.3 (-0.9 to +0.3), 8/18 | +0.3 (-0.1 to +0.7), 14/18 |
| 2 | typical | +1.8 (+0.9 to +2.7), 14/18 | +1.1 (+0.6 to +1.6), 14/18 | -0.9 (-1.3 to -0.4), 2/18 |
| 4 | mixed | -0.3 (-0.6 to +0.0), 5/18 | -0.3 (-0.5 to -0.0), 5/18 | +0.1 (-0.1 to +0.2), 13/18 |
| 4 | typical | +1.3 (+0.8 to +1.9), 16/18 | +0.6 (+0.1 to +1.1), 16/18 | -0.4 (-0.8 to -0.0), 5/18 |
| 8 | mixed | -0.3 (-0.5 to -0.1), 4/18 | -0.0 (-0.2 to +0.2), 7/18 | +0.0 (-0.1 to +0.1), 10/18 |
| 8 | typical | +0.7 (+0.4 to +1.0), 17/18 | +0.2 (-0.1 to +0.4), 15/18 | -0.2 (-0.4 to +0.0), 6/18 |
| 16 | mixed | -0.1 (-0.1 to -0.0), 7/18 | -0.0 (-0.1 to +0.0), 6/18 | -0.0 (-0.0 to +0.0), 10/18 |
| 16 | typical | +0.2 (+0.1 to +0.3), 17/18 | -0.0 (-0.2 to +0.1), 11/18 | -0.0 (-0.1 to +0.1), 8/18 |
| 32 | mixed | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 |
| 32 | typical | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 |

### Blend of own motion and crowd, 2 seconds ahead

| k | Arm | Coverage, average viewer | Coverage, worst 10% | Poor seconds per minute, worst 10% |
|---|---|---|---|---|
| 1 | mixed | +0.0 (-0.1 to +0.1), 11/18 | -0.0 (-0.1 to +0.1), 8/18 | +0.0 (-0.0 to +0.1), 11/18 |
| 1 | typical | +0.1 (-0.0 to +0.2), 14/18 | +0.1 (+0.0 to +0.3), 14/18 | -0.1 (-0.2 to -0.0), 3/18 |
| 2 | mixed | -0.0 (-0.1 to +0.0), 7/18 | -0.0 (-0.1 to -0.0), 6/18 | +0.0 (+0.0 to +0.1), 14/18 |
| 2 | typical | +0.1 (+0.1 to +0.2), 16/18 | +0.2 (+0.2 to +0.3), 18/18 | -0.1 (-0.2 to -0.1), 2/18 |
| 4 | mixed | -0.0 (-0.1 to -0.0), 5/18 | -0.0 (-0.1 to -0.0), 6/18 | +0.0 (-0.0 to +0.1), 13/18 |
| 4 | typical | +0.1 (+0.1 to +0.2), 17/18 | +0.2 (+0.1 to +0.2), 17/18 | -0.1 (-0.2 to -0.0), 4/18 |
| 8 | mixed | -0.0 (-0.0 to -0.0), 6/18 | +0.0 (-0.0 to +0.1), 9/18 | -0.0 (-0.1 to +0.0), 10/18 |
| 8 | typical | +0.1 (-0.0 to +0.1), 14/18 | +0.0 (-0.2 to +0.2), 13/18 | -0.1 (-0.2 to +0.0), 6/18 |
| 16 | mixed | -0.0 (-0.0 to +0.0), 7/18 | -0.0 (-0.1 to +0.0), 9/18 | +0.0 (-0.0 to +0.0), 11/18 |
| 16 | typical | +0.0 (-0.0 to +0.1), 11/18 | -0.1 (-0.3 to +0.1), 11/18 | -0.1 (-0.1 to +0.0), 5/18 |
| 32 | mixed | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 |
| 32 | typical | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 |

### Blend, 5 seconds ahead

| k | Arm | Coverage, average viewer | Coverage, worst 10% | Poor seconds per minute, worst 10% |
|---|---|---|---|---|
| 1 | mixed | +0.0 (-0.1 to +0.2), 12/18 | +0.1 (-0.1 to +0.2), 13/18 | -0.0 (-0.1 to +0.1), 7/18 |
| 1 | typical | +0.3 (+0.2 to +0.5), 16/18 | +0.4 (+0.3 to +0.5), 18/18 | -0.2 (-0.3 to -0.0), 5/18 |
| 2 | mixed | -0.1 (-0.3 to +0.0), 7/18 | -0.1 (-0.3 to +0.0), 6/18 | +0.1 (-0.0 to +0.1), 14/18 |
| 2 | typical | +0.5 (+0.3 to +0.7), 16/18 | +0.6 (+0.4 to +0.8), 18/18 | -0.3 (-0.5 to -0.2), 5/18 |
| 4 | mixed | -0.1 (-0.2 to -0.0), 5/18 | -0.1 (-0.2 to +0.1), 5/18 | +0.0 (-0.1 to +0.1), 12/18 |
| 4 | typical | +0.4 (+0.3 to +0.6), 17/18 | +0.3 (-0.1 to +0.5), 17/18 | -0.2 (-0.5 to +0.1), 2/18 |
| 8 | mixed | -0.1 (-0.2 to -0.0), 4/18 | +0.0 (-0.1 to +0.2), 8/18 | -0.1 (-0.2 to -0.0), 7/18 |
| 8 | typical | +0.2 (+0.1 to +0.3), 15/18 | -0.1 (-0.6 to +0.3), 13/18 | +0.2 (-0.2 to +0.6), 11/18 |
| 16 | mixed | -0.0 (-0.1 to +0.0), 5/18 | +0.0 (-0.1 to +0.1), 8/18 | -0.0 (-0.1 to +0.0), 11/18 |
| 16 | typical | +0.1 (-0.0 to +0.1), 14/18 | -0.2 (-0.5 to +0.1), 9/18 | +0.1 (-0.1 to +0.3), 9/18 |
| 32 | mixed | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 |
| 32 | typical | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 |

## Same comparison with style taken from the same experiment only (crowd only)

Here a viewer's style for a test video uses just the other eight videos of that experiment,
so nothing depends on viewer numbers matching across the two experiments.

| k | Arm | Coverage, average viewer | Coverage, worst 10% | Poor seconds per minute, worst 10% |
|---|---|---|---|---|
| 1 | mixed | +0.5 (-0.9 to +2.0), 12/18 | -0.3 (-1.6 to +0.8), 11/18 | +0.2 (-0.5 to +1.1), 6/18 |
| 1 | typical | +3.5 (+1.7 to +4.9), 17/18 | +2.3 (+1.0 to +3.3), 16/18 | -1.6 (-2.3 to -0.7), 3/18 |
| 2 | mixed | +0.1 (-0.3 to +0.5), 9/18 | +0.1 (-0.2 to +0.4), 9/18 | -0.0 (-0.2 to +0.2), 8/18 |
| 2 | typical | +2.7 (+2.1 to +3.3), 18/18 | +1.5 (+0.9 to +2.1), 16/18 | -1.0 (-1.4 to -0.5), 2/18 |
| 4 | mixed | -0.7 (-1.0 to -0.4), 1/18 | -0.1 (-0.4 to +0.3), 5/18 | -0.0 (-0.2 to +0.2), 9/18 |
| 4 | typical | +1.4 (+1.0 to +1.9), 18/18 | +0.5 (-0.0 to +1.0), 14/18 | -0.2 (-0.4 to +0.1), 6/18 |
| 8 | mixed | -0.3 (-0.7 to -0.1), 6/18 | +0.2 (+0.0 to +0.6), 12/18 | -0.1 (-0.2 to -0.0), 7/18 |
| 8 | typical | +0.8 (+0.5 to +1.2), 17/18 | +0.2 (-0.4 to +0.5), 14/18 | -0.0 (-0.2 to +0.2), 7/18 |
| 16 | mixed | -0.2 (-0.4 to -0.1), 3/18 | +0.1 (-0.0 to +0.4), 9/18 | -0.0 (-0.1 to +0.1), 6/18 |
| 16 | typical | +0.3 (+0.1 to +0.5), 18/18 | -0.1 (-0.4 to +0.1), 12/18 | +0.0 (-0.1 to +0.1), 9/18 |
| 32 | mixed | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 |
| 32 | typical | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 | +0.0 (+0.0 to +0.0), 0/18 |

# 4 chosen viewers against 16 random viewers

Written by `scripts/four_vs_sixteen.py` from the same trials as `chosen_vs_random.md`.
Each number is (group of 4) minus (random group of 16), averaged over 18 held-out videos, with a
95% bootstrap interval over videos and the count of videos where the group of four did better.

## Crowd only

| Group of 4 | Coverage, average viewer (points) | Coverage, worst 10% of viewers (points) | Poor seconds per minute, worst 10% | Verdict on average coverage |
|---|---|---|---|---|
| mixed | -3.4 (-4.0 to -2.8), 0/18 | -1.8 (-2.5 to -1.0), 2/18 | +0.8 (+0.3 to +1.3), 2/18 | sixteen beat four |
| typical | -1.8 (-2.3 to -1.3), 0/18 | -0.9 (-1.4 to -0.4), 1/18 | +0.3 (-0.1 to +0.9), 5/18 | sixteen beat four |
| random | -3.1 (-3.7 to -2.5), 0/18 | -1.5 (-2.1 to -0.8), 2/18 | +0.7 (+0.2 to +1.2), 3/18 | sixteen beat four |

## Blend, 2 s ahead

| Group of 4 | Coverage, average viewer (points) | Coverage, worst 10% of viewers (points) | Poor seconds per minute, worst 10% | Verdict on average coverage |
|---|---|---|---|---|
| mixed | -0.5 (-0.8 to -0.3), 3/18 | -1.0 (-1.5 to -0.4), 2/18 | +1.0 (+0.7 to +1.3), 1/18 | sixteen beat four |
| typical | -0.4 (-0.6 to -0.1), 4/18 | -0.8 (-1.3 to -0.2), 4/18 | +0.9 (+0.6 to +1.2), 2/18 | sixteen beat four |
| random | -0.5 (-0.8 to -0.2), 3/18 | -1.0 (-1.5 to -0.3), 2/18 | +1.0 (+0.7 to +1.3), 2/18 | sixteen beat four |

## Blend, 5 s ahead

| Group of 4 | Coverage, average viewer (points) | Coverage, worst 10% of viewers (points) | Poor seconds per minute, worst 10% | Verdict on average coverage |
|---|---|---|---|---|
| mixed | -1.8 (-2.4 to -1.1), 3/18 | -1.1 (-2.5 to +1.1), 3/18 | +0.0 (-2.5 to +1.6), 3/18 | sixteen beat four |
| typical | -1.2 (-1.8 to -0.7), 3/18 | -0.7 (-2.3 to +1.6), 3/18 | -0.2 (-2.8 to +1.5), 4/18 | sixteen beat four |
| random | -1.7 (-2.3 to -1.0), 3/18 | -1.0 (-2.4 to +1.2), 3/18 | +0.0 (-2.5 to +1.5), 3/18 | sixteen beat four |

## How many random viewers is a group of four worth?

Read off the random-group curve for average coverage, crowd only. A value of 4 means the
choice added nothing. The curve was measured from 1 to 32 viewers, so values stop there.

| Group of 4 | Equivalent number of random viewers |
|---|---|
| mixed | 3.8 |
| typical | 6.4 |

## By experiment (crowd only, average coverage, points)

Nine videos each, so these intervals are wide.

| Group of 4 | Experiment 1 (free viewing) | Experiment 2 (live events, told to follow) |
|---|---|---|
| mixed | -4.2 (-4.7 to -3.8) | -2.6 (-3.7 to -1.8) |
| typical | -2.5 (-3.3 to -1.8) | -1.1 (-1.6 to -0.7) |
| random | -3.9 (-4.2 to -3.6) | -2.3 (-3.3 to -1.5) |

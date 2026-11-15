# Is viewing style a stable trait?

Written by `scripts/chosen_vs_random.py` before any outcome is computed. Each feature is a
z-score among the 48 viewers of a video. The table gives the correlation across viewers
between a feature's average on one set of videos and on a disjoint set. Near 1 means the
feature belongs to the person. Near 0 means it belongs to the moment.

| Split | Head speed | Exploration | On the crowd |
|---|---|---|---|
| odd vs even videos, all | 0.88 | 0.80 | 0.62 |
| odd vs even videos, experiment 1 | 0.89 | 0.84 | 0.39 |
| odd vs even videos, experiment 2 | 0.87 | 0.75 | 0.81 |
| experiment 1 vs experiment 2 | 0.51 | 0.36 | 0.29 |

The last row doubles as a check on viewer numbers. If folder 17 were a different person
in the two experiments, these correlations would be near zero.

## Spread between viewers (raw values, averaged over the 18 videos)

| Feature | Lowest viewer | Median | Highest viewer |
|---|---|---|---|
| Head speed (degrees per second) | 6.7 | 12.4 | 25.4 |
| Exploration (bits) | 2.30 | 2.83 | 3.76 |
| On the crowd (share of window) | 0.66 | 0.78 | 0.84 |

## How the features relate (correlation of viewers' average z-scores)

| | Head speed | Exploration | On the crowd |
|---|---|---|---|
| head_speed | 1.00 | 0.80 | -0.51 |
| exploration | 0.80 | 1.00 | -0.58 |
| on_crowd | -0.51 | -0.58 | 1.00 |

At least one feature is stable enough to group viewers by, so the comparison goes ahead.

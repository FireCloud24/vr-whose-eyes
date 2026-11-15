# Why did the mixed group not help? Two checks

Written by `scripts/why_not_mixed.py`. Crowd only, 200 trials per video, 18 held-out videos.

## 1. Is it just the tight budget?

Differences from a random group of the same size, as in `chosen_vs_random.md`, at other budgets.

### 12 of 72 tiles

| k | Arm | Coverage, average viewer | Coverage, worst 10% | Poor seconds per minute, worst 10% |
|---|---|---|---|---|
| 1 | mixed | +0.1 (-1.7 to +1.7), 12/18 | -0.3 (-1.9 to +1.1), 11/18 | -0.1 (-1.2 to +1.1), 5/18 |
| 1 | typical | +2.4 (+0.8 to +3.7), 17/18 | +1.7 (+1.1 to +2.4), 16/18 | -1.8 (-2.4 to -1.3), 2/18 |
| 2 | mixed | -0.4 (-1.2 to +0.3), 5/18 | -0.2 (-0.7 to +0.4), 8/18 | +0.2 (-0.4 to +0.7), 11/18 |
| 2 | typical | +1.9 (+1.1 to +2.6), 15/18 | +1.2 (+0.7 to +1.7), 15/18 | -1.3 (-1.9 to -0.7), 3/18 |
| 4 | mixed | -0.3 (-0.6 to -0.1), 3/18 | -0.2 (-0.4 to -0.0), 6/18 | +0.1 (-0.1 to +0.2), 12/18 |
| 4 | typical | +1.3 (+0.8 to +1.8), 15/18 | +0.6 (+0.1 to +1.0), 14/18 | -0.5 (-1.0 to -0.1), 3/18 |
| 8 | mixed | -0.3 (-0.5 to -0.1), 3/18 | -0.0 (-0.2 to +0.2), 9/18 | +0.1 (-0.0 to +0.2), 13/18 |
| 8 | typical | +0.6 (+0.4 to +1.0), 17/18 | +0.2 (-0.1 to +0.5), 14/18 | -0.3 (-0.6 to -0.1), 3/18 |
| 16 | mixed | -0.1 (-0.1 to -0.0), 4/18 | -0.1 (-0.1 to +0.0), 8/18 | +0.1 (+0.0 to +0.2), 15/18 |
| 16 | typical | +0.2 (+0.1 to +0.3), 16/18 | +0.1 (-0.0 to +0.2), 12/18 | -0.1 (-0.2 to +0.1), 6/18 |

### 24 of 72 tiles

| k | Arm | Coverage, average viewer | Coverage, worst 10% | Poor seconds per minute, worst 10% |
|---|---|---|---|---|
| 1 | mixed | +0.0 (-2.1 to +1.9), 12/18 | -0.6 (-2.6 to +1.1), 12/18 | +0.6 (-0.6 to +2.0), 7/18 |
| 1 | typical | +2.3 (+0.5 to +3.7), 17/18 | +2.1 (+1.4 to +2.7), 17/18 | -1.1 (-1.5 to -0.7), 2/18 |
| 2 | mixed | -0.4 (-0.9 to +0.2), 6/18 | -0.3 (-1.0 to +0.4), 7/18 | +0.2 (-0.3 to +0.9), 11/18 |
| 2 | typical | +1.3 (+0.7 to +2.0), 15/18 | +0.8 (+0.2 to +1.4), 14/18 | -0.3 (-0.8 to +0.1), 3/18 |
| 4 | mixed | -0.2 (-0.4 to -0.0), 4/18 | -0.2 (-0.6 to +0.1), 8/18 | +0.1 (-0.1 to +0.4), 10/18 |
| 4 | typical | +1.0 (+0.7 to +1.4), 16/18 | +0.4 (-0.1 to +0.8), 14/18 | -0.1 (-0.5 to +0.3), 7/18 |
| 8 | mixed | -0.2 (-0.3 to -0.0), 6/18 | +0.0 (-0.1 to +0.3), 9/18 | -0.1 (-0.3 to +0.0), 9/18 |
| 8 | typical | +0.6 (+0.4 to +0.8), 18/18 | +0.0 (-0.4 to +0.4), 13/18 | +0.2 (-0.0 to +0.4), 11/18 |
| 16 | mixed | -0.1 (-0.1 to -0.0), 3/18 | +0.0 (-0.1 to +0.1), 8/18 | -0.0 (-0.1 to +0.1), 7/18 |
| 16 | typical | +0.2 (+0.1 to +0.3), 17/18 | -0.5 (-1.1 to +0.0), 7/18 | +0.4 (+0.1 to +0.8), 12/18 |

## 2. Do viewers of one kind predict viewers of the same kind?

Coverage % of test viewers (rows) when the 4 earlier viewers all come from one third of the pool
(columns), 16 tiles. Thirds are by activity score from the other videos.

| Test viewers | Group of calm viewers | Group of middle viewers | Group of active viewers |
|---|---|---|---|
| calm | 74.6 (67.4 to 81.1) | 74.9 (68.1 to 81.2) | 73.6 (66.7 to 79.9) |
| middle | 75.1 (68.1 to 81.5) | 75.1 (68.2 to 81.6) | 74.1 (67.2 to 80.5) |
| active | 72.2 (65.6 to 78.3) | 72.5 (66.1 to 78.6) | 71.6 (65.0 to 77.7) |

Own kind minus the average of the other two kinds, paired by video (points, 95% interval, videos above zero):

| Test viewers | Own kind minus others |
|---|---|
| calm | +0.3 (-0.5 to +1.1), 11/18 |
| middle | +0.6 (+0.0 to +1.2), 11/18 |
| active | -0.8 (-1.4 to -0.2), 5/18 |

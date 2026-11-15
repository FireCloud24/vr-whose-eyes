# Baselines: own motion, random crowds, and a blend

Written by `scripts/baselines.py`. Budget 16 of 72 tiles. Each video is a held-out test:
200 random splits into 16 test viewers and a pool of 32, with groups drawn at random from the
pool. Numbers are means over the 18 videos with 95% bootstrap intervals over videos.
Coverage is the share of the viewer's window in high quality. "Poor seconds" are
seconds per minute with coverage under 50%.

## Own motion (no other viewers)

| Horizon | Coverage % | Worst 10% of viewers, coverage % | Poor seconds per minute | Worst 10%, poor seconds |
|---|---|---|---|---|
| 1 s | 86.8 (84.6 to 88.9) | 76.5 (73.3 to 79.7) | 4.1 (3.1 to 5.1) | 9.8 (7.7 to 11.9) |
| 2 s | 81.9 (78.9 to 84.9) | 69.1 (64.6 to 73.5) | 7.2 (5.5 to 8.9) | 15.4 (12.3 to 18.5) |
| 5 s | 74.9 (70.6 to 79.3) | 60.3 (54.4 to 66.2) | 11.4 (8.6 to 14.1) | 21.3 (17.1 to 25.5) |

## Crowd of k random viewers (same at every horizon)

| k | Coverage % | Worst 10% of viewers, coverage % | Poor seconds per minute | Worst 10%, poor seconds |
|---|---|---|---|---|
| 1 | 66.9 (59.9 to 73.6) | 53.8 (45.3 to 62.4) | 15.9 (11.3 to 20.7) | 24.9 (18.6 to 31.1) |
| 2 | 70.2 (63.4 to 76.7) | 57.3 (49.1 to 65.5) | 13.7 (9.2 to 18.6) | 23.2 (16.9 to 29.5) |
| 4 | 73.8 (67.1 to 80.0) | 59.4 (51.1 to 67.8) | 11.6 (7.5 to 16.2) | 21.7 (15.6 to 28.0) |
| 8 | 75.8 (69.4 to 81.7) | 60.5 (52.1 to 68.8) | 10.7 (6.8 to 15.0) | 21.2 (15.2 to 27.5) |
| 16 | 76.9 (70.8 to 82.5) | 61.0 (52.5 to 69.3) | 10.1 (6.5 to 14.2) | 21.0 (15.0 to 27.3) |
| 32 | 77.4 (71.5 to 82.9) | 61.1 (52.6 to 69.5) | 9.9 (6.4 to 13.8) | 20.9 (15.0 to 27.2) |

## Blend of own motion and the crowd: coverage %

| k | 1 s ahead | 2 s ahead | 5 s ahead |
|---|---|---|---|
| 1 | 86.9 (84.7 to 89.0) | 81.9 (78.7 to 85.0) | 76.4 (72.0 to 80.7) |
| 2 | 86.9 (84.8 to 89.0) | 82.7 (79.5 to 85.7) | 77.3 (72.7 to 81.8) |
| 4 | 87.1 (84.9 to 89.2) | 82.9 (79.8 to 85.9) | 77.9 (73.3 to 82.4) |
| 8 | 87.2 (85.1 to 89.3) | 83.2 (80.0 to 86.2) | 79.0 (74.3 to 83.5) |
| 16 | 87.3 (85.1 to 89.4) | 83.4 (80.3 to 86.4) | 79.6 (75.1 to 83.9) |
| 32 | 87.3 (85.2 to 89.4) | 83.5 (80.4 to 86.5) | 79.8 (75.4 to 84.0) |

## Weight on own motion in the blend

Chosen for each test video from the other 17 videos. The table shows the most common choice
across test videos.

| k | 1 s ahead | 2 s ahead | 5 s ahead |
|---|---|---|---|
| 1 | 0.9 | 0.9 | 0.7 |
| 2 | 0.9 | 0.7 | 0.5 |
| 4 | 0.7 | 0.7 | 0.5 |
| 8 | 0.7 | 0.5 | 0.3 |
| 16 | 0.7 | 0.5 | 0.3 |
| 32 | 0.7 | 0.5 | 0.3 |

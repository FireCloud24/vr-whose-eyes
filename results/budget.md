# Choosing the tile budget

Written by `scripts/baselines.py`. The frame has 72 tiles. With perfect foresight,
meaning the system fetches exactly the tiles the viewer goes on to look at, this is
the share of the viewer's window that a budget can cover:

| Budget (tiles) | Share of the frame | Mean over videos | Lowest video |
|---|---|---|---|
| 8 | 11% | 63.3% | 62.1% |
| 12 | 17% | 84.8% | 83.3% |
| 16 | 22% | 96.8% | 95.3% |
| 20 | 28% | 99.4% | 98.8% |
| 24 | 33% | 99.8% | 99.7% |

Rule: take the smallest budget where perfect foresight covers at least
95%. That is **16 tiles**. The rule looks only at perfect foresight, never at how a
predictor scores. A smaller budget cannot serve even a perfectly predicted viewer, and a
larger one makes every predictor look good.

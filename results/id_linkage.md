# Do viewer IDs link across videos?

Written by `scripts/check_ids.py`. The files carry no name or device id, so this
is the evidence the recordings themselves give.

## What is on disk

| | Viewer folders | Session files |
|---|---|---|
| Experiment 1 | 48 (numbered 1 to 48) | 432 |
| Experiment 2 | 48 (numbered 1 to 48) | 432 |

The single demographics file lists 48 viewers. Its numbers match the folder numbers in both experiments.

## Within an experiment

- 94 of 96 folders are one sitting: nine videos recorded in play order
  within two hours. The median sitting lasted 45 minutes.
- Pairs of sessions from different folders that overlap in time: 0.
  There was one headset, so an overlap would mean the clocks or the folders are wrong.
- Folders that are not one clean sitting:

| Experiment | Viewer | Videos | In play order | Span (minutes) |
|---|---|---|---|---|
| 1 | 9 | 9 | no | 76464 |
| 1 | 19 | 9 | yes | 6057 |

  These look like one video recorded again later. I keep them.

## Across the two experiments

The paper says 48 participants took part in the experiments, and it ships one
demographics file for both. It never says in so many words that folder 17 is the
same person in both. The recordings add this:

| Check | Value |
|---|---|
| Rank correlation of folder number with recording order, experiment 1 | 0.54 |
| Rank correlation of folder number with recording order, experiment 2 | -0.20 |
| Headset height, odd vs even videos of one sitting, experiment 1 (r) | 0.99 |
| Headset height, odd vs even videos of one sitting, experiment 2 (r) | 0.97 |
| Headset height, experiment 1 vs experiment 2 (r) | 0.37 |
| Permutation p-value for that correlation being above zero | 0.0053 |

How to read it. If numbers had been handed out afresh as people arrived, folder
number would follow recording order in both experiments. Headset height is a
weak trace of a person: it also depends on the chair and on how the tracking was
set up that day, so I expect a modest correlation across experiments at best.

## Verdict

- Within an experiment, a folder is one person. 98% of folders are one sitting and 0 sessions overlap.
- Across experiments, the recordings support the link but cannot prove it: folder numbers are not simply arrival order in both experiments, and headset height agrees more than chance.
- So every result that carries a viewer's style across experiments should also be
  shown using videos from the same experiment only.

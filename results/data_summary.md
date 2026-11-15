# The data, one row per video

Written by `scripts/heatmaps.py`. Every viewer is put on the video's own clock at
10 samples a second. "Missing" is the share of samples with no recorded row within
0.25 seconds. "Top 16 tiles" is the share of all viewing that lands on the 16
most-watched of the 72 tiles, so a high value means everyone looks at the same place.

| Video | Title | Category | Viewers | Length (s) | Missing | Median head speed (deg/s) | Within 30 deg of horizon | Top 16 tiles |
|---|---|---|---|---|---|---|---|---|
| 1-1 | Conan360-Sandwich | Performance | 48 | 164 | 0.00% | 6.5 | 95% | 75% |
| 1-2 | Freestyle Skiing | Sport | 48 | 201 | 0.00% | 9.4 | 90% | 61% |
| 1-3 | Google Spotlight-HELP | Film | 48 | 293 | 0.00% | 6.7 | 86% | 53% |
| 1-4 | Conan360-Weird Al | Performance | 48 | 172 | 0.00% | 7.4 | 94% | 77% |
| 1-5 | GoPro VR-Tahiti Surf | Sport | 48 | 206 | 0.00% | 11.3 | 91% | 46% |
| 1-6 | The Fight for Falluja | Documentary | 48 | 655 | 1.32% | 7.6 | 94% | 61% |
| 1-7 | 360 Cooking Battle | Performance | 48 | 451 | 0.00% | 2.5 | 97% | 56% |
| 1-8 | LOSC Football | Sport | 48 | 165 | 0.00% | 9.1 | 91% | 67% |
| 1-9 | The Last of the Rhinos | Documentary | 48 | 292 | 0.00% | 6.2 | 84% | 58% |
| 2-1 | Weekly Idol-Dancing | Performance | 48 | 278 | 0.00% | 3.7 | 100% | 90% |
| 2-2 | Damai Music Live-Vocie Toy | Performance | 48 | 341 | 0.02% | 4.3 | 98% | 83% |
| 2-3 | Rio Olympics VR Interview | Talkshow | 48 | 186 | 0.00% | 2.5 | 99% | 82% |
| 2-4 | Female Basketball Match | Sport | 48 | 361 | 0.88% | 3.7 | 99% | 77% |
| 2-5 | SHOWTIME Boxing | Sport | 48 | 172 | 0.00% | 2.5 | 99% | 93% |
| 2-6 | Gear 360: Anitta | Performance | 48 | 206 | 0.29% | 6.3 | 98% | 54% |
| 2-7 | 2016 CCTV Spring Festival Gala | Performance | 48 | 373 | 0.00% | 4.1 | 99% | 88% |
| 2-8 | VR Concert | Performance | 48 | 226 | 0.00% | 5.5 | 94% | 86% |
| 2-9 | Hey VR Interview | Talkshow | 48 | 520 | 0.00% | 3.1 | 99% | 86% |

| Experiment | Videos | Total minutes | Median head speed (deg/s) | Top 16 tiles |
|---|---|---|---|---|
| 1 | 9 | 43 | 7.4 | 61% |
| 2 | 9 | 44 | 4.0 | 82% |

# Related work, in plain English

This note says what earlier work did and where my project sits. I read the dataset
paper and the two arXiv papers in full or in large part. I know 360BroadView and
CUB360 only from their abstracts and from how other papers describe them, and I
say so below.

## The problem

A 360° video is far bigger than what a headset shows at any moment. A viewer sees
roughly a 100° window of it. So streaming systems cut the picture into tiles and
send the tiles they expect the viewer to look at in high quality, and the rest in
low quality or not at all. The system has to guess a second or more ahead, because
video is fetched in chunks before it is shown. A wrong guess means the viewer turns
their head and sees a blurry patch.

There are three sources for the guess: where this viewer's head has just been,
what is in the video, and where earlier viewers of the same video looked.

## The dataset

**Wu, Tan, Wang and Yang, "A Dataset for Exploring User Behaviors in VR Spherical
Video Streaming" (MMSys 2017).** 48 people watched 18 videos on an HTC Vive while
sitting on a swivel chair, in two experiments about a week apart. The first
experiment used nine mixed videos and let people look around freely. The second
used nine recordings of live events (concerts, sport, talk shows) and told people
there would be a short quiz afterwards, so that they would follow the content. The
logs give head orientation about 90 times a second. The paper also gives each
viewer's age band, gender and VR experience.

The paper shows that people in the second experiment stay near the horizon and
near one region of interest, and that head speed differs a lot between people. It
does not ask whether a person's way of watching carries over from one video to the
next. My project depends on that, so I test it.

## Using only the viewer's own motion

**Romero Rondón, Sassatelli, Aparicio-Pardo and Precioso, "TRACK: A New Method from
a Re-examination of Deep Architectures for Head Motion Prediction in 360° Videos"
(arXiv 1911.11702).** This paper re-ran several published deep models that predict
head motion from past positions plus the video content. Its uncomfortable finding
is that all of them did worse than simple baselines that use the viewer's past
trajectory alone. The authors then built TRACK, which does beat those baselines,
with the largest gains at 2 to 5 seconds ahead on videos with a clear focus. They
also found that content only starts to help beyond about 2 to 3 seconds.

TRACK deliberately does not use other viewers' traces. I take two things from it.
First, a plain own-motion baseline is strong at short horizons and must be in every
comparison. Second, the interesting horizon for anything else is 2 seconds and
beyond, so I report 1, 2 and 5 seconds.

## Using other viewers

**Li, Zhang, Liu and Wang, "Very Long Term Field of View Prediction for 360-degree
Video Streaming" (arXiv 1902.01439).** This paper predicts 1 to 10 seconds ahead.
It combines the viewer's own past trajectory with where other viewers looked at the
same moment of the same video. It treats the other viewers as "experts" and learns
how much weight to give each one from how similar they are to the target viewer.
It reports that other viewers' data helps a lot at long horizons, and that the
exact way of mixing them in matters little. It tests on this same Tsinghua dataset,
after training on another one.

**Ban et al., "CUB360: Exploiting Cross-Users Behaviors for Viewport Prediction in
360 Video Adaptive Streaming" (ICME 2018).** As I understand it from its abstract
and from the two papers above, it predicts the viewer's position by linear
regression on their own motion and then corrects it towards the nearest positions
of other viewers.

Both papers assume a store of earlier viewers and ask how to weight them for one
target viewer at prediction time. Neither asks the earlier question: if only a few
people can watch first, who should they be?

## Choosing which viewers to learn from

**Zhou, Yang, Guo, Tian and Nahrstedt, "360BroadView: Viewer Management for
Viewport Prediction in 360-Degree Video Live Broadcast" (ACM Multimedia Asia
2022).** This is the closest work I found, and I have read only its abstract. In a
live broadcast nobody has watched the video before. The system lets some viewers
with good bandwidth watch slightly ahead ("leading viewers") and uses their head
motion to predict for everyone else ("lagging viewers"). The paper is about keeping
enough leading viewers as people join and leave. So it manages how many leading
viewers there are. As far as I can tell it does not ask what kind of viewers they
should be.

## Where my project sits

Earlier work shows that other viewers help, and that a similarity-weighted crowd
is better than a plain average. The setting where this matters most is a new or
live video, where the crowd is small. My question is about that small crowd. With
k earlier viewers and a fixed number of high-quality tiles, I compare a group
picked to cover different viewing styles against a random group of the same size,
and I look at the worst-served viewers as well as the average.

Two ways this could turn out to be uninteresting, which is why it is worth testing:

- Viewing style may not be a stable trait. If a person who explores in one video
  sits still in the next, there is nothing to choose by.
- Even if style is stable, a crowd heatmap may only need bodies. Then four chosen
  viewers will not beat sixteen random ones, and the quantity explanation holds.

I think the worst-served viewers are the right place to look. An average can hide
the people a system fails, and in a headset those are the people who feel ill.

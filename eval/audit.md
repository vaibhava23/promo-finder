# Blind audit of the tool's final top 30 (heuristic mode)

Rater: a single rater who also built the tool, so there is a bias risk; a Kuku editor should re-rate.
Checks from the brief: **H** hook lands in first 3 s · **C** ends unresolved · **S** makes sense to a stranger.

| # | Segments | H | C | S | Note |
|---|---|---|---|---|---|
| 1 | E24 00:32.50–01:08.00 | ✓ | ✓ | ✓ |  |
| 2 | E23 01:19.00–02:04.00 | ✓ | ✓ | ✓ |  |
| 3 | E3 01:24.00–01:38.50 + E3 02:13.20–02:25.75 | ✓ | ✓ | ✓ | fight, then he kneels; her answer withheld |
| 4 | E27 00:44.50–01:20.50 | ✗ | ✓ | ✗ | 'husband's name?' only lands if you saw the ring |
| 5 | E29 00:40.10–00:59.00 + E29 01:24.00–01:48.80 | ✓ | ✗ | ✓ | ends on a lament, not a question |
| 6 | E15 00:47.40–01:22.40 | ✓ | ✓ | ✓ |  |
| 7 | E12 00:44.00–01:27.21 | ✓ | ✓ | ✓ |  |
| 8 | E28 00:38.20–01:15.10 | ✓ | ✓ | ✓ |  |
| 9 | E1 00:39.10–01:14.30 | ✓ | ✓ | ✓ | the show's premise, episode 1 |
| 10 | E27 00:17.20–00:46.40 | ✓ | ✓ | ✓ |  |
| 11 | E3 01:00.50–01:25.50 | ✓ | ✓ | ✓ |  |
| 12 | E27 01:58.70–02:23.80 | ✓ | ✓ | ✓ |  |
| 13 | E7 00:38.20–01:09.50 | ✓ | ✓ | ✓ |  |
| 14 | E23 00:58.50–01:24.00 | ✗ | ✓ | ✓ | 'Mother.' is not a hook |
| 15 | E38 00:11.00–00:47.50 | ✗ | ✓ | ✓ | opens on a kindness, not a jolt |
| 16 | E3 00:13.80–00:43.30 | ✓ | ✓ | ✓ |  |
| 17 | E12 00:05.70–00:43.50 | ✓ | ✓ | ✓ |  |
| 18 | E18 01:26.50–01:55.50 + E18 02:51.80–03:06.50 | ✓ | ✓ | ✓ |  |
| 19 | E36 01:59.80–02:28.00 | ✓ | ✓ | ✓ |  |
| 20 | E36 02:26.50–02:50.80 + E36 03:00.00–03:20.75 | ✓ | ✓ | ✓ |  |
| 21 | E28 01:44.20–02:11.00 | ✓ | ✓ | ✓ |  |
| 22 | E35 02:06.00–02:37.50 | ✓ | ✓ | ✗ | 'Ashwood' and the conspiracy need context |
| 23 | E46 01:18.10–01:40.40 + E46 02:07.20–02:18.50 | ✓ | ✓ | ✗ | church/council trial needs context |
| 24 | E30 02:05.50–02:31.21 | ✓ | ✓ | ✓ |  |
| 25 | E25 01:20.20–01:47.00 | ✓ | ✓ | ✓ |  |
| 26 | E36 01:39.50–02:06.80 | ✓ | ✓ | ✓ |  |
| 27 | E42 00:18.00–00:33.80 + E42 00:44.80–01:12.50 | ✓ | ✗ | ✓ | ends on the reveal itself (a resolution) |
| 28 | E32 00:16.20–00:49.00 | ✓ | ✓ | ✗ | book-burning stakes unclear alone |
| 29 | E35 01:29.80–02:05.50 | ✓ | ✓ | ✗ | war-conspiracy backstory |
| 30 | E43 01:09.00–01:52.50 | ✓ | ✓ | ✗ | 'Lord Sterling' unexplained |

**Pass rates:** hook 27/30 · cliffhanger 28/30 · standalone 24/30 · **all three 20/30 (67%)** · at least two 29/30 · **top 10 all-three: 8/10**

Previous version (before the resolution and dropped-setup fixes): all three 17/30, top 10 7/10.

Cross-episode variants (V01–V10, not ranked): about 4 of 10 are usable as is (V04 altar→'A better choice?', V05, V07, V01); the rest need an editor or the LLM judge.

Main remaining failure: **standalone**, i.e. plot-dependent names (Sterling, Ashwood, the council). An LLM 'context' score is designed for exactly this.
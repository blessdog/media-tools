# The exploration film — technique map (prior art → our tools)

2026-08-19. Ryan's brief: explore the ENTIRE artwork under his narration
(art-history channel), 1930s-Disney look, water alive in every shot,
gusts not constant sway, enhance-never-regenerate. Disney is the proven
foundation, not a ceiling — use later innovations where they beat it.

## Anchor prior art

**The Old Mill (Disney, 1937)** — first multiplane camera film; Academy
Award. Mood piece with no dialogue: one location explored through
weather, light, and living detail. Their toolbox and our equivalent:

| Disney 1937 | mechanism | ours |
|---|---|---|
| Multiplane camera | artwork on glass levels moving at different speeds | zone card stacks + render-parallax --plane-fit (proven) |
| Effects animation (Cy Young, Ugo D'Orsi et al.) | specialists animate ONLY water/rain/wind over held cels | animate-strokes wave/sway per region over the locked plate (proven) |
| Cycles on held scenes | short loops of ripples etc. while the scene holds | our 3s stroke cycles (proven; can't invent new strokes — fine on ≤3-4s holds, watch longer) |
| Wind as EVENT, not state | a gust arrives, bends things base-first, passes, dies | GAP: animate-strokes sway is continuous. Needs a gust ENVELOPE (attack-decay over N frames). Small additive flag. |
| Camera drift on holds | almost-imperceptible truck keeps a held shot alive | trivial: tiny fov/x ramp in any path |
| Timing for mood | speed of a move IS the emotion | path durations from the narration beats |
| Rotation of 3D objects | the mill's rotating machinery | out of scope (nothing rotates in the scroll) |

**River of Wisdom (Crystal CG, Expo 2010)** — 清明上河图 animated at 1:1
museum scale (128m screen, 12 projectors): moving water, walking figures,
boats, day/night over the REAL scroll. Existence proof that an animated
Chinese handscroll IS a museum-grade product — Ryan's channel does per-
painting what they did as an installation. Their figures walk on the real
painting = our walk-figure lane. (Deeper technique details: follow-up
research when figure passes begin.)

## Modern layer (post-Disney innovations we already embody or should)

- **2.5D / camera projection** (documentary standard since The Kid Stays
  in the Picture, 2002): cut layers + parallax camera — literally our
  card stack. Their lesson: reserve parallax for moments; most shots are
  flat pans with LIFE, not depth moves.
- **Layer-space fill** (our inpaint-planes --flux): the modern answer to
  Disney painting each glass level complete. Fill once, flicker impossible.
- **Subpixel pan discipline** (already measured here: integer rounding =
  machine shimmer, walk-figure pans sample subpixel). Applies to every
  ffmpeg/window pan we author.

## The grammar this buys (for the script, when it lands)

Default shot = a HELD or slowly-floating frame anywhere in the scroll,
water always cycling, occasional gust through foliage; camera pans/zooms
between narration subjects; 3D peek-around (cards) only where the script
lingers on a spatial detail. No z-push-as-identity. The fixated Ge crop
is retired; the whole 105MP scroll is the set.

## Build queue implied

1. Gust envelope flag in animate-strokes (attack/hold/decay, per-region
   phase offsets so gusts travel across the frame).
2. Native-res water/fall cycles for ALL water regions (regions.json).
3. Float/pan path idiom for render-living at native k (subpixel windows).
4. Later, with the script: walk-figure passes; peek-around card moments.

Sources: [The Old Mill — Wikipedia](https://en.wikipedia.org/wiki/The_Old_Mill),
[The Kid Should See This](https://thekidshouldseethis.com/post/old-mill-walt-disney-silly-symphony),
[River of Wisdom — New Atlas](https://newatlas.com/crystal-cg-digital-animated-tapestry/16108/),
[China.org.cn on the Expo scroll](http://www.china.org.cn/travel/2010-10/20/content_21162825.htm),
[SCMP: 4D interactive Qingming scroll](https://www.scmp.com/culture/arts-entertainment/article/2154396/classic-chinese-painting-brought-life-4d-interactive)

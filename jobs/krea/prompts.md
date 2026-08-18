# Drafted prompts — NOT APPROVED, NOT SUBMITTED

Six subjects, taken from the photos Ryan dropped 2026-08-12. Read, cut, rewrite.

## The register

Krea LoRAs are trigger-phrase driven: the medium lives in the weights, so the
text carries **content only** — who, where, what, framing — and ends with the
trigger. No "ink", "wash", "brush" or "paper" anywhere except the trigger.
Describing the look in words fights the LoRA, which is the failure that wrecked
the earlier prompts.

```
darkbrush     → "…, monochrome ink wash style"
linen scroll  → "…, chinese ink linen scroll style"
```

---

**S1 · man and hound in a car** — close portrait plus an animal. Two faces in
one frame is the hardest thing here; the linen-scroll LoRA has no published
sample with a face at all.

> A man with a heavy moustache and round tinted glasses sits in a car
> passenger seat, a large bloodhound filling the seat beside him, the dog's
> long ears hanging down. Grey upholstery behind them.

**S2 · snowboarder** — wide landscape with a figure. The register both LoRAs
are demonstrably strongest at.

> A snowboarder in a white suit stands on a snowy slope holding a board under
> one arm, pointing up at a range of jagged snow-covered peaks. Cloud sits in
> the valley below.

**S3 · doorway** — dim interior, hard prop, unheroic. This is the tonal-mismatch
control: darkbrush's samples are samurai and wraiths, and if it turns a laundry
room into a fantasy scene, that is the thing samples cannot tell you.

> A man in headphones steps through a doorway holding a large kitchen knife at
> his side. Behind him a washing machine and a dryer in a dim narrow room.

**S4 · hound on a rock** — animal alone, water, foliage, no human face.

> A large bloodhound lies on a broad boulder at the edge of a green river,
> looking off to one side. Scrub and rocks line the far bank.

**S5 · poppy pod, macro** — extreme close detail, droplets, no figure. Tests
whether the style survives when there is no silhouette to carry it.

> A single pale green poppy seed pod fills the frame, its crown splayed open,
> beads of sap running down its side. Foliage blurred behind.

**S6 · poppy stand** — botanical plus a mundane suburban background. Nature
against parked cars and a sidewalk.

> A cluster of pale poppy seed pods on tall stems in a front garden. Behind
> them a residential street, a parked car, and a low brick house.

---

## Matrix

6 subjects × 2 LoRAs × 2 bases (turbo, raw) = **24 renders**, one seed
throughout so the only variables are the ones being tested.

| | |
|---|---|
| bases | `krea2_turbo_fp8_scaled` and `krea2_raw_fp8_scaled` — both on the box |
| LoRA strength | 1.0 |
| seed | one, reused everywhere |
| steps / cfg | read from ComfyUI's official Krea-2 template, NOT guessed — turbo is distilled and wants far fewer steps than raw |
| aspect | 16:9 |

Expect raw to look weaker at first: both LoRAs are tagged against turbo, and a
LoRA trained on a distilled base does not always transfer to the full one. If
that happens it is the transfer failing, not raw being worse — the fix is LoRA
strength and step count.

## Waiting on

Cut, rewrite, or say go.

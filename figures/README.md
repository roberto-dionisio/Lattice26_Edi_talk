# Figures

Every figure in the deck is generated here as an SVG and embedded by relative path
from `optimal_annealing.qmd`. Nothing is drawn by hand, so a parameter tweak is
always a one-line edit plus a re-run.

## Regenerating

```bash
python3 figures/make_figures.py          # all figures
python3 figures/make_figures.py fig07    # just one (keys: fig02 … fig12)
quarto render                            # rebuild the deck
```

Requires `numpy` + `matplotlib`. Run from the project root.

## Layout

| file | what it does |
|---|---|
| `talkstyle.py` | the palette, the rcParams, and `save()`. Import and call `ts.use()` first. |
| `make_figures.py` | one function per figure, named after the slide it lives on. |
| `fonts/` | Fira Sans TTFs — the deck's font, so figure text matches slide text. |
| `data/` | optional real data for slide 12 (see below). Absent by default. |

Which figure is on which slide:

| key | slide | figure |
|---|---|---|
| `fig02` | 2 | power law vs. exponential critical slowing down |
| `fig03` | 3 | particle on a ring, three topological sectors |
| `fig04` | 4 | the annealing family `p_0 → p_target` |
| `fig05` | 5 | uniform vs. clustered schedule |
| `fig07` | 7 | the Fisher metric `g(λ)` |
| `fig08` | 8 | the `(β_bulk, β_defect)` plane |
| `fig09` | 9 | defect on the lattice, rings of constant `d(x,y)` |
| `fig12` | 12 | results: learned field + learned vs. theoretical trajectory |

## The color contract

Four colors, four fixed meanings, reused in every figure so the audience only has
to learn the visual language once. Defined in `talkstyle.py`, mirrored in
`theme.scss` so the slides agree with the plots.

| role | color | |
|---|---|---|
| bulk coupling, bulk quantities | `#23373B` dark teal | metropolis primary |
| defect coupling, the defect site | `#EB811B` orange | metropolis secondary |
| easy / reference distribution `p_0` | `#3B7EA1` steel blue | |
| target distribution `p_target` | `#9C162A` crimson | metropolis alert |

The corollary the figures lean on: **crimson always means hard / frozen /
exponential, blue always means easy / free.** That is why the exponential curve on
slide 2 and the wound sectors on slide 3 are crimson, while the defect that
unfreezes them is orange. On slide 12 the heatmap colormap literally interpolates
orange → teal, i.e. defect coupling → bulk coupling.

Two supporting neutrals (`INK`, `MUTED`, `FAINT`) carry structure only — axes,
guides, strawman paths — and never meaning.

## Slide 12 is synthetic until you say otherwise

The results panels currently show a **placeholder**: a plausible-looking coupling
field and a learned trajectory built as the theoretical geodesic plus small
wobbles. It is illustrative, not a measurement. Swap in the real thing by dropping
either of these files into `figures/data/` — `make_figures.py` picks them up
automatically and says so when it does:

```
figures/data/beta_field.npy           # 2D array: the learned beta(x,y,t) field
figures/data/learned_trajectory.npy   # (N,2) array: columns [beta_bulk, beta_defect]
```

The theoretical geodesic itself comes from `theory_geodesic()`, which slides 8 and
12 both call — so the curve the audience sees on slide 8 is the same curve the
learned trajectory is compared against on slide 12. Replace that function when you
have the real Fisher geodesic.

## Font

`talkstyle.py` registers the TTFs in `fonts/` with matplotlib, so figure text is
set in Fira Sans, same as the slides. Glyphs are exported as outlines
(`svg.fonttype: path`), so the SVGs render identically on any projector without
needing the font installed. If `fonts/` were ever emptied, the script warns and
falls back to DejaVu Sans rather than failing.

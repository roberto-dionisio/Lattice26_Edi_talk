"""
Shared visual language for every figure in the talk.

Import this before plotting anything:

    import talkstyle as ts
    ts.use()

It registers Fira Sans (the deck's font, bundled in figures/fonts/), sets a
minimal "paper figure" rcParams, and exposes the four semantic colors.

THE COLOR CONTRACT
------------------
Four colors, four meanings, used the same way in every figure so the audience
learns the visual language once:

    BULK    dark teal   bulk coupling / bulk quantities        (theme primary)
    DEFECT  orange      defect coupling / the defect site      (theme secondary)
    EASY    steel blue  easy / reference distribution p_0      (tractable, unfrozen)
    TARGET  crimson     target distribution p_target           (hard, frozen, the problem)

Corollary used throughout: crimson always means "hard/frozen/exponential",
blue always means "easy/free". That is why the exponential curve on slide 2 and
the wound sectors on slide 3 are crimson, and the defect that unfreezes them is
orange.

BULK and DEFECT are the metropolis theme's own primary/secondary, so the figures
read as part of the slides rather than as pasted-in plots.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).parent
OUT = HERE  # SVGs land next to this script, in figures/

# --- the four semantic colors -------------------------------------------------
BULK = "#23373B"    # metropolis primary
DEFECT = "#EB811B"  # metropolis secondary
EASY = "#3B7EA1"
TARGET = "#9C162A"  # metropolis alert

# --- supporting neutrals (structure only, never carry meaning) -----------------
INK = "#33474B"     # body text color of the theme
MUTED = "#8A9AA0"
FAINT = "#C9D2D5"

PALETTE = {"bulk": BULK, "defect": DEFECT, "easy": EASY, "target": TARGET}


def _register_fonts() -> str:
    """Make the bundled Fira Sans visible to matplotlib. Falls back gracefully."""
    fonts = sorted((HERE / "fonts").glob("*.ttf"))
    for f in fonts:
        font_manager.fontManager.addfont(str(f))
    available = {f.name for f in font_manager.fontManager.ttflist}
    if "Fira Sans" in available:
        return "Fira Sans"
    print("  ! Fira Sans not found in figures/fonts/ -- falling back to DejaVu Sans.")
    print("  ! Figure text will not match the slide font. See figures/README.md.")
    return "DejaVu Sans"


def use() -> None:
    """Apply the talk-wide matplotlib style."""
    family = _register_fonts()

    mpl.rcParams.update({
        # Type: same face as the slides, light weight like the theme body text.
        "font.family": "sans-serif",
        "font.sans-serif": [family, "Helvetica", "Arial", "DejaVu Sans"],
        "font.weight": "light",
        "font.size": 11,
        # Math set to the same face, so "tau" in an axis label matches the prose.
        "mathtext.fontset": "custom",
        "mathtext.rm": family,
        "mathtext.it": f"{family}:italic",
        "mathtext.bf": f"{family}:bold",
        "mathtext.default": "it",
        # Paper-figure chrome: two thin spines, no grid, ticks out and short.
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.titlecolor": BULK,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "axes.grid": False,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelcolor": INK,
        "ytick.labelcolor": INK,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
        "legend.frameon": False,
        "legend.fontsize": 10,
        "text.color": INK,
        # Transparent canvas so the slide background (#f1f1f1) shows through, and
        # glyphs as outlines so the SVG renders identically wherever it's projected.
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "savefig.facecolor": "none",
        "savefig.transparent": True,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "svg.fonttype": "path",
    })


def save(fig, name: str) -> None:
    """Write <name>.svg into figures/ and report it."""
    path = OUT / f"{name}.svg"
    fig.savefig(path, format="svg")
    plt.close(fig)
    print(f"  wrote {path.relative_to(HERE.parent)}")


def bare(ax, keep=("bottom", "left")) -> None:
    """Strip an axes down to the spines you actually want."""
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(side in keep)

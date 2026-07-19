#!/usr/bin/env python3
"""
Generate every figure in the talk as an SVG, into figures/.

    python3 figures/make_figures.py            # all figures
    python3 figures/make_figures.py fig07 res_field  # just these

One function per figure, named after the slide it lives on. Tweak the constants
at the top of a function and re-run; nothing else in the deck needs touching.

The results figures (res_geometry, res_swaps, res_field) read measured data from
../results/*.npz -- nothing there is synthetic. See results/*_README.md.
"""

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import FancyArrowPatch, Rectangle, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).parent))
import talkstyle as ts
from talkstyle import BULK, DEFECT, EASY, TARGET, INK, MUTED, FAINT

DATA = Path(__file__).parent / "data"

TWO_PI = 2 * np.pi


# =============================================================================
# Slide 2 -- two flavors of critical slowing down
# =============================================================================
def fig02_critical_slowing_down():
    z = 2.0        # dynamical critical exponent, tau ~ a^-z
    c = 1.0        # tau_top ~ exp(c/a)

    inv_a = np.linspace(1.0, 7.0, 400)
    tau_std = inv_a**z                      # power law in 1/a
    tau_top = np.exp(c * inv_a) / np.exp(c)  # exponential, matched at 1/a = 1

    fig, ax = plt.subplots(figsize=(6.4, 4.0))

    # The two curves and their labels carry SVG group ids (gids). The overlay step
    # below turns each into a reveal fragment so it can draw itself on -- see
    # _emit_fig02_overlay(). The base frame (axes, continuum arrow) has no gid, so
    # it is always visible.
    (l_std,) = ax.semilogy(inv_a, tau_std, color=EASY, lw=2.2)
    l_std.set_gid("curve-std")
    (l_top,) = ax.semilogy(inv_a, tau_top, color=TARGET, lw=2.4)
    l_top.set_gid("curve-top")

    # Label the curves at their far ends -- a legend box would just be one more
    # thing to read, and the gap at the right edge IS the point of the figure.
    a_std = ax.annotate(r"$\tau \sim a^{-z}$", xy=(inv_a[-1], tau_std[-1]),
                        xytext=(7, -1), textcoords="offset points",
                        color=EASY, fontsize=13, va="center")
    a_std.set_gid("label-std")
    a_top = ax.annotate(r"$\tau_{\mathrm{top}} \sim e^{\,c/a}$",
                        xy=(inv_a[-1], tau_top[-1]),
                        xytext=(7, 0), textcoords="offset points",
                        color=TARGET, fontsize=13, va="center")
    a_top.set_gid("label-top")

    ax.set_xlabel(r"$1/a$")
    ax.set_ylabel(r"$\tau$   (log scale)")
    ax.set_xlim(1.0, 8.6)
    ax.set_ylim(0.8, 1.2e3)
    ax.set_xticks([])
    ax.set_yticks([])
    ts.bare(ax)

    # "a -> 0" is the direction of the continuum limit: say so on the axis.
    ax.annotate("", xy=(0.62, -0.155), xytext=(0.16, -0.155),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.0,
                                shrinkA=0, shrinkB=0, mutation_scale=11))
    ax.text(0.64, -0.155, r"continuum limit   $a \to 0$", transform=ax.transAxes,
            color=MUTED, fontsize=10, va="center")

    ts.save(fig, "fig02_critical_slowing_down")


def _emit_fig02_overlay():
    """Turn the static slide-2 SVG into an inline, animatable partial.

    Reads figures/fig02_critical_slowing_down.svg and writes
    figures/_fig02_overlay.qmd -- a raw-HTML block holding the same SVG inline, but
    with each curve/label group tagged as a reveal fragment. The deck includes that
    partial instead of the <img>, so the curves can draw themselves on in sync with
    the equations on the left (matching data-fragment-index values). See the CSS in
    theme.scss (svg.anim-fig) and the getTotalLength() script in the .qmd header.
    """
    import re

    src = ts.OUT / "fig02_critical_slowing_down.svg"
    svg = src.read_text()
    svg = svg[svg.index("<svg"):]  # drop the <?xml?> / <!DOCTYPE> preamble

    # Let CSS size it: strip the fixed pt width/height, keep the viewBox.
    svg = re.sub(r'(<svg\b[^>]*?)\s+width="[^"]*"\s+height="[^"]*"',
                 r"\1", svg, count=1)
    svg = svg.replace("<svg ", '<svg class="anim-fig" ', 1)

    # gid -> (extra classes, fragment step). Curves get .draw-line (stroke reveal),
    # labels just fade; each shares its step with the matching equation on the left.
    # Steps 0 and 1 line up with the "Standard" and "Topological" fragments on the
    # slide -- keep these in sync with the fragment-index values in the .qmd.
    groups = {
        "curve-std": ("fragment draw-line", 0),
        "label-std": ("fragment", 0),
        "curve-top": ("fragment draw-line", 1),
        "label-top": ("fragment", 1),
    }
    for gid, (cls, idx) in groups.items():
        needle = f'<g id="{gid}">'
        if needle not in svg:
            raise RuntimeError(f"gid {gid!r} not found in SVG -- did matplotlib "
                               f"change its group markup?")
        svg = svg.replace(
            needle, f'<g id="{gid}" class="{cls}" data-fragment-index="{idx}">', 1)

    partial = ts.HERE / "_fig02_overlay.qmd"
    partial.write_text("```{=html}\n" + svg.rstrip() + "\n```\n")
    print(f"  wrote {partial.relative_to(ts.HERE.parent)}")


# =============================================================================
# Slide 3 -- particle on a ring: worldlines on the space-time box
# =============================================================================
# Worldline convention: Euclidean time tau runs UP the y-axis, position x(tau)
# along the x-axis. The box is a periodic cell -- space wraps with period 2*pi*R
# (the ring), time with period beta -- so a path that leaves one edge re-enters
# the opposite one. The topological charge Q is the net number of times the path
# winds around the ring as tau goes 0 -> beta; a winding path therefore crosses
# the box boundary and shows up as two pieces.
def _fluct(s, coeffs):
    """Fluctuation built from sine harmonics that vanish at s = 0, 1, so the path's
    endpoints stay identified (x(beta) = x(0) mod 2*pi*R) whatever the winding."""
    out = np.zeros_like(s)
    for k, a in enumerate(coeffs, start=1):
        out = out + a * np.sin(k * np.pi * s)
    return out


def fig03_ring_sectors():
    L = 1.0     # ring circumference, labelled 2*pi*R
    B = 1.0     # Euclidean time period, labelled beta
    s = np.linspace(0.0, 1.0, 700)
    tau = B * s
    x0 = 0.50 * L

    # Unwrapped worldlines X(s): the winding is the linear Q*L*s term, the wiggle is
    # a fixed set of harmonics.
    X_q0 = x0 + _fluct(s, [0.22, 0.16, -0.05]) * L
    X_p1 = x0 + L * s + _fluct(s, [0.10, 0.07]) * L

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(8.4, 4.5), sharey=True)

    def box(ax, label, color):
        ax.add_patch(Rectangle((0, 0), L, B, fill=False, edgecolor=INK,
                               lw=1.1, zorder=1))
        ax.text(0.93 * L, 0.90 * B, label, color=color, fontsize=13,
                ha="right", va="center")
        ax.text(.5 * L, -0.02 * B, r"$x(\tau)$", color=INK, fontsize=14,
                ha="left", va="top")
        ax.text(-0.03 * L, 0.5 * B, r"$\tau$", color=INK, fontsize=14,
                ha="right", va="bottom")
        ax.set_xlim(-0.04 * L, 1.10 * L)
        ax.set_ylim(-0.04 * B, 1.10 * B)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ts.bare(ax, keep=())

    def draw_wrapped(ax, X, gid, **kw):
        # wrap into the cell, break the line where it crosses an edge, and gid each
        # piece so the overlay step can animate them (see _emit_fig03_overlay).
        x = np.mod(X, L)
        jumps = np.where(np.abs(np.diff(x)) > 0.5 * L)[0]
        for i, seg in enumerate(np.split(np.arange(len(x)), jumps + 1)):
            (ln,) = ax.plot(x[seg], tau[seg], zorder=3, **kw)
            ln.set_gid(f"{gid}-{i}")

    # --- Panel A: Q = 0 -- wanders off and comes back, no net winding -------
    draw_wrapped(axA, X_q0, "wl-q0", color=EASY, lw=2.4)
    box(axA, "Q = 0", EASY)

    # --- Panel B: Q = +1 -- drifts right, wraps at the x = 2*pi*R edge -------
    draw_wrapped(axB, X_p1, "wl-p1", color=TARGET, lw=2.4)
    box(axB, "Q = +1", TARGET)

    fig.subplots_adjust(wspace=0.16)
    ts.save(fig, "fig03_ring_sectors")


def _emit_fig03_overlay():
    """Inline, animatable copy of the slide-3 figure (cf. _emit_fig02_overlay).

    Both worldlines draw themselves on with the stroke effect. The Q = +1 path is
    two pieces because it wraps across the periodic edge; the second piece carries
    .draw-seq2 so it starts only once the first has reached the edge, so the pen
    appears to run bottom -> right edge -> (reappear at left edge) -> top, following
    the spatial periodicity. Steps: 0 = Q=0, 1 = Q=+1.
    """
    import re

    src = ts.OUT / "fig03_ring_sectors.svg"
    svg = src.read_text()
    svg = svg[svg.index("<svg"):]
    svg = re.sub(r'(<svg\b[^>]*?)\s+width="[^"]*"\s+height="[^"]*"', r"\1", svg, count=1)
    svg = svg.replace("<svg ", '<svg class="anim-fig ring-fig" ', 1)

    # Sequence: fragment 0 = setup text (boxes empty), fragment 1 draws Q=0,
    # fragment 2 draws Q=+1 (its two wrap pieces in order). Keep these indices in
    # sync with the text fragments in the .qmd.
    groups = {
        "wl-q0-0": ("fragment draw-line", 1),              # Q=0 draws at step 1
        "wl-p1-0": ("fragment draw-line", 2),              # Q=+1 bottom piece, step 2
        "wl-p1-1": ("fragment draw-line draw-seq2", 2),    # Q=+1 top piece, waits for it
    }
    for gid, (cls, idx) in groups.items():
        needle = f'<g id="{gid}">'
        if needle not in svg:
            raise RuntimeError(f"gid {gid!r} not found in fig03 SVG -- did the wrap "
                               f"produce a different number of segments?")
        svg = svg.replace(
            needle, f'<g id="{gid}" class="{cls}" data-fragment-index="{idx}">', 1)

    partial = ts.HERE / "_fig03_overlay.qmd"
    partial.write_text("```{=html}\n" + svg.rstrip() + "\n```\n")
    print(f"  wrote {partial.relative_to(ts.HERE.parent)}")


# =============================================================================
# Slide 4 -- annealing: a family of distributions from easy to target
# =============================================================================
def _bimodal(x, lam):
    """p_lambda: one broad easy bump at lambda=0, two sharp separated modes at
    lambda=1. The barrier -- and with it the freezing -- grows along the way."""
    d = 1.75 * lam            # mode separation
    s = 1.05 - 0.72 * lam     # mode width
    g = lambda m: np.exp(-0.5 * ((x - m) / s) ** 2)
    p = 0.5 * (g(-d) + g(+d))
    return p / p.max()


def _blend(c1, c2, t):
    """Linear RGB blend of two hex colors."""
    import matplotlib.colors as mc
    a, b = np.array(mc.to_rgb(c1)), np.array(mc.to_rgb(c2))
    return tuple(a + (b - a) * t)


def fig04_annealing_family():
    lams = [0.0, 0.25, 0.5, 0.75, 1.0]
    labels = [r"$p_0$", "", r"$p_\lambda$", "", r"$p_{\mathrm{target}}$"]

    fig, axes = plt.subplots(1, len(lams), figsize=(9.6, 2.5))

    x = np.linspace(-3.2, 3.2, 400)
    for i, (ax, lam) in enumerate(zip(axes, lams)):
        color = _blend(EASY, TARGET, lam)
        p = _bimodal(x, lam)
        ax.fill_between(x, p, color=color, alpha=0.16, lw=0)
        ax.plot(x, p, color=color, lw=2.2)

        ax.set_ylim(0, 1.2)
        ax.set_xlim(x[0], x[-1])
        ax.set_xticks([])
        ax.set_yticks([])
        ts.bare(ax, keep=())
        # Label sits just above the curve's peak, not up in the panel margin.
        ax.text(0.5, 0.9, labels[i], transform=ax.transAxes, ha="center", va="bottom",
                color=color if labels[i] else "none", fontsize=13)

    # One arrow underneath carries the whole story: lambda sweeps 0 -> 1.
    arrow = FancyArrowPatch((0.045, 0.055), (0.965, 0.055),
                            transform=fig.transFigure, figure=fig,
                            arrowstyle="-|>", mutation_scale=13,
                            color=MUTED, lw=1.0, shrinkA=0, shrinkB=0)
    fig.patches.append(arrow)
    fig.text(0.5, 0.105, r"$\lambda \;:\; 0 \;\longrightarrow\; 1$",
             ha="center", color=MUTED, fontsize=12)

    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.2, wspace=0.25)
    ts.save(fig, "fig04_annealing_family")


# =============================================================================
# Slide 5 -- where do you spend a fixed budget of steps?
# =============================================================================
def fig05_schedule_ticks():
    n = 11
    t = np.linspace(0, 1, n)

    uniform = t
    # Push points toward the middle: same budget, spent where the going gets hard.
    s = 2 * t - 1
    clustered = 0.5 + 0.5 * np.sign(s) * np.abs(s) ** 1.75

    fig, ax = plt.subplots(figsize=(9.0, 2.6))

    ax.plot([0, 1], [1, 1], color=INK, lw=1.0, solid_capstyle="butt")
    for xx, col in ((0.0, EASY), (1.0, TARGET)):
        ax.plot([xx], [1], "o", color=col, ms=8, clip_on=False, zorder=3)
    ax.text(0.0, 1.13, r"$p_0$", color=EASY, fontsize=14, ha="center")
    ax.text(1.0, 1.13, r"$p_{\mathrm{target}}$", color=TARGET, fontsize=14, ha="center")

    rows = [
        (uniform,   0.62, MUTED, "naive: uniform schedule"),
        (clustered, 0.20, BULK,  "optimal:  ?"),
    ]
    for pos, y, color, label in rows:
        ax.vlines(pos, y - 0.10, y + 0.10, color=color, lw=1.8)
        ax.text(-0.035, y, label, color=color, fontsize=12.5, ha="right", va="center")

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(0.0, 1.3)
    ax.set_xticks([])
    ax.set_yticks([])
    ts.bare(ax, keep=())

    fig.subplots_adjust(left=0.30, right=0.98, top=0.9, bottom=0.05)
    ts.save(fig, "fig05_schedule_ticks")


def _emit_fig05_schedule():
    """Animated, fragment-driven twin of fig05, as an inline-SVG partial.

    Same style as the static figure, but each piece is a reveal fragment so it
    appears on its own key press: (0) the two endpoints, (1) the connecting arrow,
    (2) the naive uniform tick row, (3) the optimal row -- which starts at the
    uniform positions and then rearranges into the clustered 'dense in the middle'
    schedule. The rearrangement is animated by the sched-anim script in the .qmd
    header, which reads each optimal tick's data-u (uniform x) and data-c (clustered
    x). Writes figures/_fig05_schedule.qmd.
    """
    x0, W = 215.0, 505.0
    xr = x0 + W
    y_line, y_naive, y_opt, th = 52.0, 128.0, 190.0, 13.0

    t = np.linspace(0, 1, 11)
    uni = x0 + t * W
    s = 2 * t - 1
    clu = x0 + (0.5 + 0.5 * np.sign(s) * np.abs(s) ** 1.75) * W

    def tick(x, y, color, cls="", extra=""):
        return (f'<line class="{cls}" x1="{x:.1f}" y1="{y - th:.1f}" '
                f'x2="{x:.1f}" y2="{y + th:.1f}" stroke="{color}" '
                f'stroke-width="2.4" stroke-linecap="round"{extra}/>')

    def plabel(x, color, sub):
        return (f'<text x="{x:.1f}" y="{y_line - 20:.0f}" text-anchor="middle" '
                f'fill="{color}" font-size="19" font-style="italic">p'
                f'<tspan baseline-shift="sub" font-size="0.7em" '
                f'font-style="normal">{sub}</tspan></text>')

    P = []
    P.append('<svg class="sched-anim" viewBox="0 0 760 224" '
             'xmlns="http://www.w3.org/2000/svg" '
             'style="width:100%;max-width:900px;height:auto;display:block;'
             'margin:0.4em auto">')

    # (0) endpoints + labels
    P.append('<g class="fragment" data-fragment-index="1">')
    P.append(f'<circle cx="{x0:.0f}" cy="{y_line:.0f}" r="7" fill="{EASY}"/>')
    P.append(f'<circle cx="{xr:.0f}" cy="{y_line:.0f}" r="7" fill="{TARGET}"/>')
    P.append(plabel(x0, EASY, "0"))
    P.append(plabel(xr, TARGET, "target"))
    P.append('</g>')

    # (1) connecting line + centred arrowhead (p_0 -> p_target)
    xm = (x0 + xr) / 2
    P.append('<g class="fragment" data-fragment-index="2">')
    P.append(f'<line x1="{x0:.0f}" y1="{y_line:.0f}" x2="{xr:.0f}" '
             f'y2="{y_line:.0f}" stroke="{INK}" stroke-width="2"/>')
    P.append(f'<path d="M {xm - 7:.0f} {y_line - 7:.0f} L {xm + 8:.0f} '
             f'{y_line:.0f} L {xm - 7:.0f} {y_line + 7:.0f} Z" fill="{INK}"/>')
    P.append('</g>')

    # (2) naive uniform ticks
    P.append('<g class="fragment" data-fragment-index="3">')
    for x in uni:
        P.append(tick(x, y_naive, MUTED))
    P.append(f'<text x="{x0 - 24:.0f}" y="{y_naive + 5:.0f}" text-anchor="end" '
             f'fill="{MUTED}" font-size="14">naive: uniform schedule</text>')
    P.append('</g>')

    # (3) optimal ticks: born uniform, rearrange to clustered
    P.append('<g class="fragment" data-fragment-index="4" id="sched-optrow">')
    for xu, xc in zip(uni, clu):
        P.append(tick(xu, y_opt, BULK, cls="opt-tick",
                      extra=f' data-u="{xu:.1f}" data-c="{xc:.1f}"'))
    P.append(f'<text x="{x0 - 24:.0f}" y="{y_opt + 5:.0f}" text-anchor="end" '
             f'fill="{BULK}" font-size="14" font-weight="500">'
             f'optimal: ?</text>')
    P.append('</g>')

    P.append('</svg>')

    partial = ts.HERE / "_fig05_schedule.qmd"
    partial.write_text("```{=html}\n" + "\n".join(P) + "\n```\n")
    print(f"  wrote {partial.relative_to(ts.HERE.parent)}")


# =============================================================================
# CP^(N-1) methods -- the defect that anneals open -> periodic boundaries
# =============================================================================
def fig_defect_anneal():
    """Two lattices sharing a defect seam (the middle column of horizontal links).
    Left: lambda=0, the defect coupling is off -> that column is cut -> open in the
    horizontal direction. Right: lambda=1, the defect is healed at the bulk coupling
    -> fully periodic. Annealing lambda drives beta_defect from 0 to beta_bulk."""
    nx, ny = 6, 5
    xs, ys = np.meshgrid(range(nx), range(ny))

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.8, 4.1))

    def panel(ax, healed, lam, bc):
        for i in range(nx):                                  # vertical links (bulk)
            ax.plot([i, i], [0, ny - 1], color=BULK, lw=1.4, zorder=1)
        for j in range(ny):                                  # horizontal links
            ax.plot([0, 2], [j, j], color=BULK, lw=1.4, zorder=1)
            ax.plot([3, nx - 1], [j, j], color=BULK, lw=1.4, zorder=1)
            if healed:                                       # defect link (col 2-3)
                ax.plot([2, 3], [j, j], color=DEFECT, lw=2.8, zorder=2)
        ax.plot([2.5, 2.5], [-0.5, ny - 0.5], color=DEFECT, lw=1.2,
                ls=(0, (3, 3)), alpha=0.75, zorder=0)         # the seam
        ax.plot(xs.ravel(), ys.ravel(), "o", color=MUTED, ms=5.5, zorder=3)
        ax.text(2.5, ny - 0.35, "defect", color=DEFECT, fontsize=11,
                ha="center", va="bottom")
        ax.set_title(lam, color=INK, fontsize=15, pad=12)
        ax.text(0.5, -0.13, bc, transform=ax.transAxes, ha="center",
                color=INK, fontsize=12.5)
        ax.set_xlim(-0.6, nx - 0.4)
        ax.set_ylim(-1.0, ny - 0.1)
        ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        ts.bare(ax, keep=())

    panel(axL, False, r"$\lambda = 0$",
          r"OBC:  $\beta_{\mathrm{def}} = 0$")
    panel(axR, True, r"$\lambda = 1$",
          r"PBC:  $\beta_{\mathrm{def}} = \beta_{\mathrm{bulk}}$")

    # annealing arrow between the two lattices
    arrow = FancyArrowPatch((0.475, 0.52), (0.525, 0.52),
                            transform=fig.transFigure, figure=fig,
                            arrowstyle="-|>", mutation_scale=16,
                            color=MUTED, lw=1.4, shrinkA=0, shrinkB=0)
    fig.patches.append(arrow)
    fig.text(0.5, 0.6, r"anneal", ha="center", color=MUTED, fontsize=11)

    fig.subplots_adjust(left=0.04, right=0.96, top=0.9, bottom=0.1, wspace=0.28)
    ts.save(fig, "fig_defect_anneal")


def fig_pt_tower():
    """Parallel tempering, drawn as the swap actually happens. A ladder of replicas
    (lambda=0, ..., lambda, lambda+1, ..., lambda=1), each running an MCMC chain left
    to right. Between the adjacent lambda / lambda+1 chains a swap is proposed: the
    two configurations cross (the '?', the accept/reject), after which each replica
    carries the other's configuration -- orange and teal trade lanes."""
    px = [0.9, 1.95, 3.0, 4.05, 5.1]           # config positions along MC time
    S = 2                                       # the step S -> S+1 is the swap
    laneL = 0.5
    dotsX = px[-1] + 0.5                         # trailing "..." (kept inside the box)
    laneR = px[-1] + 0.9
    A, B = DEFECT, BULK                         # the two swapped configurations
    easy, tgt = np.array(to_rgb(EASY)), np.array(to_rgb(TARGET))
    lam_col = lambda t: tuple(easy + (tgt - easy) * t)

    fig, ax = plt.subplots(figsize=(9.2, 5.4))

    def lane(y):
        ax.add_patch(FancyBboxPatch((laneL, y - 0.4), laneR - laneL, 0.8,
            boxstyle="round,pad=0.01,rounding_size=0.14", linewidth=0,
            facecolor="#e6eaeb", zorder=0))
    def hstep(x0, x1, y):                        # an MCMC step, labelled
        ax.annotate("", xy=(x1, y), xytext=(x0, y),
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6,
                            mutation_scale=11, shrinkA=10, shrinkB=10), zorder=2)
        ax.text((x0 + x1) / 2, y + 0.2, "MCMC", color=MUTED, fontsize=10,
                ha="center", va="bottom")
    def dot(x, y, c):
        ax.plot([x], [y], "o", color=c, ms=14, zorder=4,
                markeredgecolor="white", markeredgewidth=1.5)
    def tail(y):
        ax.text(dotsX, y, r"$\cdots$", color=MUTED, fontsize=15,
                ha="center", va="center")
    def label(y, txt, t, bc=None):
        ax.text(laneL - 0.24, y + (0.14 if bc else 0), txt, ha="right",
                va="center", color=lam_col(t), fontsize=17, fontstyle="italic")
        if bc:
            ax.text(laneL - 0.24, y - 0.21, bc, ha="right", va="center",
                    color=lam_col(t), fontsize=12, fontweight="bold")
    def ellipsis(y):
        for dy in (-0.1, 0.0, 0.1):
            ax.plot([px[2]], [y + dy], "o", color=MUTED, ms=2.4, zorder=1)

    def plain_chain(y, txt, t, bc=None):
        lane(y); label(y, txt, t, bc); tail(y)
        for i in range(len(px) - 1):
            hstep(px[i], px[i + 1], y)
        for x in px:
            dot(x, y, MUTED)

    # geometry of the rungs
    y0, ye1, yl, yl1, ye2, y1 = 5.6, 4.9, 4.2, 3.0, 2.3, 1.6

    plain_chain(y0, r"$\lambda = 0$", 0.0, bc="OBC (open)")
    ellipsis(ye1)

    # --- the swap pair: lambda (top) and lambda+1 (bottom) ------------------
    lane(yl); lane(yl1); tail(yl); tail(yl1)
    label(yl, r"$\lambda$", 0.44); label(yl1, r"$\lambda + 1$", 0.58)
    for i in (0, 1):                            # MCMC before the swap
        hstep(px[i], px[i + 1], yl); hstep(px[i], px[i + 1], yl1)
    hstep(px[S + 1], px[S + 2], yl); hstep(px[S + 1], px[S + 2], yl1)   # after
    # crossing swap arrows, coloured by the config they carry
    ax.annotate("", xy=(px[S + 1], yl1), xytext=(px[S], yl),
        arrowprops=dict(arrowstyle="-|>", color=A, lw=2.4, mutation_scale=14,
                        shrinkA=11, shrinkB=11), zorder=3)
    ax.annotate("", xy=(px[S + 1], yl), xytext=(px[S], yl1),
        arrowprops=dict(arrowstyle="-|>", color=B, lw=2.4, mutation_scale=14,
                        shrinkA=11, shrinkB=11), zorder=3)
    for i, x in enumerate(px):                  # tokens trade lanes at the swap
        dot(x, yl, A if i <= S else B)
        dot(x, yl1, B if i <= S else A)
    cx, cy = (px[S] + px[S + 1]) / 2, (yl + yl1) / 2      # the accept/reject "?"
    ax.plot([cx], [cy], "o", color="#f1f1f1", ms=22, zorder=5)
    ax.text(cx, cy, "?", ha="center", va="center", color=INK,
            fontsize=18, fontweight="bold", zorder=6)

    ellipsis(ye2)
    plain_chain(y1, r"$\lambda = 1$", 1.0, bc="PBC (periodic)")

    ax.set_xlim(-1.1, laneR + 0.4)
    ax.set_ylim(1.05, 6.25)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ts.bare(ax, keep=())
    ts.save(fig, "fig_pt_tower")


# =============================================================================
# Slide 7 -- the Fisher metric g(lambda), and where it concentrates
# =============================================================================
def _g_of_lambda(lam):
    """Schematic Fisher metric: quiet at both ends, sharply peaked at the crossover
    where the topological barriers actually form."""
    return 0.12 + np.exp(-0.5 * ((lam - 0.55) / 0.13) ** 2)


def fig07_fisher_metric():
    lam = np.linspace(0, 1, 500)
    g = _g_of_lambda(lam)

    fig, ax = plt.subplots(figsize=(6.6, 3.6))

    ax.fill_between(lam, g, color=BULK, alpha=0.10, lw=0)
    ax.plot(lam, g, color=BULK, lw=2.4)

    peak = lam[np.argmax(g)]
    ax.annotate("topological crossover",
                xy=(peak, g.max()), xytext=(peak + 0.06, g.max() + 0.30),
                color=TARGET, fontsize=12,
                arrowprops=dict(arrowstyle="-", color=TARGET, lw=1.0,
                                shrinkA=2, shrinkB=4))

    ax.text(0.055, 0.22, "barriers\nabsent", color=MUTED, fontsize=11,
            ha="center", va="bottom", linespacing=1.35)
    ax.text(0.945, 0.22, "barriers\nformed", color=MUTED, fontsize=11,
            ha="center", va="bottom", linespacing=1.35)

    ax.set_xlabel(r"$\lambda$")
    ax.set_ylabel(r"$g(\lambda)$")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.62)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([r"$0$", r"$1$"])
    ax.set_yticks([])
    ts.bare(ax)

    ts.save(fig, "fig07_fisher_metric")


# =============================================================================
# Slides 8 and 12B -- the (beta_bulk, beta_defect) plane
# =============================================================================
BETA_T = 1.0  # beta_target, in units of itself


def theory_geodesic(n=300):
    """The Fisher geodesic used on slide 8 and again on slide 12, so the audience
    sees literally the same curve twice. Bows to lower bulk coupling: the cheap way
    to raise the defect coupling is to loosen the bulk first."""
    s = np.linspace(0, 1, n)
    bow = 0.22 * np.sin(np.pi * s) ** 1.15
    beta_bulk = BETA_T - bow
    beta_defect = BETA_T * s
    return beta_bulk, beta_defect


def _plane_axes(ax, label_fs=17, tick_fs=13):
    """Shared framing for the two (beta_bulk, beta_defect) plots."""
    ax.set_xlabel(r"$\beta_{\mathrm{bulk}}$", color=BULK, fontsize=label_fs)
    ax.set_ylabel(r"$\beta_{\mathrm{defect}}$", color=DEFECT, fontsize=label_fs)
    ax.tick_params(axis="x", colors=BULK, labelsize=tick_fs)
    ax.tick_params(axis="y", colors=DEFECT, labelsize=tick_fs)
    ax.set_xlim(0.55, 1.12)
    ax.set_ylim(-0.09, 1.16)
    ax.set_xticks([BETA_T])
    ax.set_xticklabels([r"$\beta_{\mathrm{target}}$"])
    ax.set_yticks([0, BETA_T])
    ax.set_yticklabels([r"$0$", r"$\beta_{\mathrm{target}}$"])
    ts.bare(ax)


def _endpoints(ax):
    ax.plot([BETA_T], [0], "o", color=INK, ms=7, zorder=5)
    ax.plot([BETA_T], [BETA_T], "o", color=INK, ms=7, zorder=5)


def fig08_2d_plane():
    fig, ax = plt.subplots(figsize=(5.8, 4.4))

    ax.plot([BETA_T, BETA_T], [0, BETA_T], color=MUTED, lw=1.8,
            ls=(0, (5, 4)), zorder=2)
    ax.text(BETA_T + 0.018, 0.5 * BETA_T, "naive 1D path", color=MUTED,
            fontsize=11.5, rotation=90, va="center", ha="left")

    gb, gd = theory_geodesic()
    ax.plot(gb, gd, color=BULK, lw=2.6, zorder=3)
    ax.annotate("Fisher geodesic ?", xy=(gb[210], gd[210]), xytext=(0.60, 0.98),
                color=BULK, fontsize=12.5, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=BULK, lw=0.9,
                                shrinkA=3, shrinkB=4))

    _endpoints(ax)
    _plane_axes(ax)

    fig.subplots_adjust(left=0.16, right=0.98, top=0.95, bottom=0.16)
    ts.save(fig, "fig08_2d_plane")


# =============================================================================
# Slide 9 -- the defect is a point on the lattice; distance is a coordinate
# =============================================================================
def fig09_defect_lattice():
    L = 9
    cx = cy = L // 2

    fig, ax = plt.subplots(figsize=(4.8, 4.4))

    for i in range(L):
        ax.plot([0, L - 1], [i, i], color=FAINT, lw=0.7, zorder=0)
        ax.plot([i, i], [0, L - 1], color=FAINT, lw=0.7, zorder=0)

    xs, ys = np.meshgrid(np.arange(L), np.arange(L))
    ax.plot(xs.ravel(), ys.ravel(), "o", color=MUTED, ms=3.0, zorder=2)

    # Rings of constant d(x,y): the only thing the network is allowed to see.
    for r in (1, 2, 3, 4):
        ax.add_patch(plt.Circle((cx, cy), r, fill=False, ec=DEFECT,
                                lw=0.9, ls=(0, (3, 3)), alpha=0.55, zorder=1))

    ax.plot([cx], [cy], "o", color=DEFECT, ms=11, zorder=4)
    ax.text(cx, cy - 0.55, "defect", color=DEFECT, fontsize=11.5,
            ha="center", va="top")

    ax.annotate("", xy=(cx + 3, cy + 2), xytext=(cx, cy),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1,
                                shrinkA=5, shrinkB=3, mutation_scale=10), zorder=5)
    ax.text(cx + 1.35, cy + 1.35, r"$d(x,y)$", color=INK, fontsize=12,
            ha="right", va="bottom")

    ax.set_xlim(-0.9, L - 0.1)
    ax.set_ylim(-0.9, L - 0.1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ts.bare(ax, keep=())

    ts.save(fig, "fig09_defect_lattice")


# =============================================================================
# Results -- real measured data, read from ../results/
#
# Four npz files (parallel-tempering annealing of CP(N-1), N=6, L=32, disk defect,
# 18 replicas; a HyperU-Net emits a spatial coupling field beta(x,y,lambda)). Every
# array below is measured; nothing here is synthetic. See results/*_README.md.
# =============================================================================
RESULTS = Path(__file__).parent.parent / "results"

# Sequential map for a coupling field (light -> bulk teal) and a diverging map for a
# residual (easy-blue negative | neutral | defect-orange positive) -- the same four
# colors as the rest of the talk.
_SEQ_BETA = LinearSegmentedColormap.from_list("beta_seq", ["#f6f7f7", "#8fb0b4", BULK])
_DIV_DELTA = LinearSegmentedColormap.from_list("delta_div", [EASY, "#eef1f2", DEFECT])


def _res(name):
    return np.load(RESULTS / name, allow_pickle=True)


def fig_res_geometry():
    """The money panel. Left: the learned defect schedule lands on the *measured*
    Fisher/thermodynamic optimum, both bowing away from the naive linear ramp.
    Right: cumulative thermodynamic length -- straight for the learned schedule
    (equal length per step), bent for the naive one."""
    ds = _res("schedule_comparison_final_data.npz")
    dl = _res("cumulative_thermo_length_data.npz")

    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(10.6, 4.3),
        gridspec_kw=dict(width_ratios=[1.0, 1.0], wspace=0.28))

    # --- A: learned schedule vs the measured Fisher optimum -----------------
    r = ds["rep_idx"]
    axA.plot(r, ds["beta_def_base"], ls=(0, (5, 4)), color=MUTED, lw=1.8,
             label="naive: linear ramp")
    th = ds["beta_def_thermo"]
    the = float(ds["err_mult_thermo"]) * ds["beta_def_thermo_err"]
    axA.fill_between(r, th - the, th + the, color=BULK, alpha=0.15, lw=0)
    axA.plot(r, th, color=BULK, lw=2.4, label="thermo-optimal (Fisher)")
    le = ds["beta_def_learned"]
    lee = float(ds["err_mult_learned"]) * ds["beta_def_learned_err"]
    axA.errorbar(r, le, yerr=lee, fmt="o", color=DEFECT, ms=5, mec="white",
                 mew=0.7, capsize=2, lw=1.3, label="learned (U-Net)", zorder=5)
    axA.set_xlabel(r"replica  $k$")
    axA.set_ylabel(r"$\beta_{\mathrm{defect}}$", fontsize=15)
    axA.set_xlim(-0.5, 17.5)
    axA.set_ylim(-0.1, 2.0)
    ts.bare(axA)
    axA.legend(loc="upper left", fontsize=9, handlelength=1.6, labelspacing=0.4)

    # --- B: cumulative thermodynamic length ---------------------------------
    rf = dl["rep_f"]
    axB.plot([0, 17], [0, float(dl["L_learn"])], color=FAINT, lw=1.4,
             ls=(0, (4, 4)), zorder=1)
    bf, bse = dl["basel_f"], dl["basel_se_f"]
    axB.fill_between(rf, bf - bse, bf + bse, color=MUTED, alpha=0.22, lw=0)
    axB.plot(rf, bf, color=MUTED, lw=2.2, label="naive")
    lf, lse = dl["learn_f"], dl["learn_se_f"]
    axB.fill_between(rf, lf - lse, lf + lse, color=DEFECT, alpha=0.20, lw=0)
    axB.plot(rf, lf, color=DEFECT, lw=2.4, label="learned")
    axB.set_xlabel(r"replica  $k$")
    axB.set_ylabel(r"cumulative length  $\Lambda(k)$")
    axB.set_xlim(0, 17)
    axB.set_ylim(0, 31)
    ts.bare(axB)
    axB.legend(loc="upper left", fontsize=9, handlelength=1.6, labelspacing=0.4)
    axB.text(0.97, 0.05, "straight = equal length per step",
             transform=axB.transAxes, ha="right", va="bottom",
             color=BULK, fontsize=11.5, style="italic")

    fig.subplots_adjust(left=0.07, right=0.98, top=0.94, bottom=0.14)
    ts.save(fig, "fig_res_geometry")


# The learned schedule's per-pair swap acceptance (measured), supplied directly.
_SWAP_LEARNED = np.array([
    0.26333334, 0.24337501, 0.23418751, 0.18747917, 0.21283334, 0.22345834,
    0.218827084, 0.24875001, 0.22552084, 0.213647918, 0.23681251, 0.23366667,
    0.22583334, 0.23125, 0.21204167, 0.24177084, 0.26620834])


def fig_res_swaps():
    """The operational payoff, as grouped bars. Left: parallel-tempering swap
    acceptance per rung -- the naive ladder throttles to a bottleneck at the freezing
    transition, the learned schedule keeps it uniform. Right: the sKL training loss."""
    d = _res("training_dynamic_final_data.npz")
    p = d["pair_index"]
    naive = d["swap_acc_baseline"]
    learned = _SWAP_LEARNED

    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(11.0, 4.2),
        gridspec_kw=dict(width_ratios=[1.8, 1.0], wspace=0.26))

    # --- A: swap acceptance across the ladder, grouped bars -----------------
    w = 0.42
    axA.bar(p - w / 2, naive, w, color=MUTED, label="naive")
    axA.bar(p + w / 2, learned, w, color=DEFECT, label="learned")
    j = int(np.argmin(naive))
    axA.annotate("bottleneck", xy=(j - w / 2, naive[j] + 0.006),
                 xytext=(j - w / 2, 0.34), ha="center", va="bottom",
                 color=TARGET, fontsize=12, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=TARGET, lw=1.4))
    axA.set_xlabel(r"swap pair  $i$  (between $i$ and $i{+}1$)")
    axA.set_ylabel("swap acceptance")
    axA.set_ylim(0, 0.45)
    axA.set_xlim(-0.8, 16.8)
    axA.set_xticks(range(0, 17, 2))
    ts.bare(axA)
    axA.legend(loc="upper center", ncol=2, fontsize=10, handlelength=1.3,
               columnspacing=1.5)

    # --- B: the training loss -----------------------------------------------
    axB.plot(d["losses"], color=BULK, lw=1.6)
    axB.set_xlabel("training step")
    axB.set_ylabel("sKL loss")
    ts.bare(axB)

    fig.subplots_adjust(left=0.06, right=0.98, top=0.94, bottom=0.15)
    ts.save(fig, "fig_res_swaps")


def fig_res_field():
    """Beyond a scalar schedule. Top row: the learned coupling field itself,
    beta(x,y,lambda) -- a plateau at the bulk value with the defect disk filling in.
    Bottom row: the residual delta = beta_learned - beta_naive the U-Net adds -- early
    it drives the defect coupling *ahead* of the ramp (orange), late it *holds it back*
    (blue), and throughout it shapes a spatial halo the sharp defect boundary (contour)
    cannot express."""
    d = _res("coupling_ladder_data.npz")
    learn, delta = d["beta_learn"], d["delta"]
    mask, t = d["defect_mask"], d["t_norm"]
    vlim, vmax = float(d["vlim_d"]), float(d["vmax_b"])
    idx = [3, 6, 9, 12, 15]

    fig, axes = plt.subplots(2, len(idx), figsize=(11.0, 5.0),
                             gridspec_kw=dict(wspace=0.10, hspace=0.10))
    for j, i in enumerate(idx):
        # top: the learned coupling field
        axt = axes[0, j]
        imt = axt.imshow(learn[i], origin="lower", cmap=_SEQ_BETA,
                         vmin=0, vmax=vmax, interpolation="bilinear")
        axt.contour(mask, levels=[0.5], colors="white", linewidths=0.8, alpha=0.8)
        axt.set_title(rf"$\lambda = {t[i]:.2f}$", color=INK, fontsize=12, pad=6)
        # bottom: the residual the net adds
        axb = axes[1, j]
        imb = axb.imshow(delta[i], origin="lower", cmap=_DIV_DELTA,
                         vmin=-vlim, vmax=vlim, interpolation="bilinear")
        axb.contour(mask, levels=[0.5], colors="0.3", linewidths=0.8, alpha=0.75)
        for ax in (axt, axb):
            ax.set_xticks([])
            ax.set_yticks([])
            ts.bare(ax, keep=())

    axes[0, 0].set_ylabel(r"learned  $\beta(x,y,\lambda)$", color=INK, fontsize=11)
    axes[1, 0].set_ylabel(r"residual  $\beta_{\mathrm{learn}}-\beta_{\mathrm{naive}}$",
                          color=INK, fontsize=11)

    cbt = fig.colorbar(imt, ax=axes[0, :], fraction=0.016, pad=0.012, aspect=13)
    cbb = fig.colorbar(imb, ax=axes[1, :], fraction=0.016, pad=0.012, aspect=13)
    for cb in (cbt, cbb):
        cb.outline.set_visible(False)
        cb.ax.tick_params(length=2.5, width=0.8, labelsize=8.5, colors=INK)
    cbt.set_ticks([0, vmax])
    cbt.set_ticklabels(["0", f"{vmax:.1f}"])
    cbb.set_ticks([-vlim, 0, vlim])
    cbb.set_ticklabels([f"$-{vlim:.2f}$", "0", f"$+{vlim:.2f}$"])
    ts.save(fig, "fig_res_field")


def fig_res_field_gif():
    """A looping animation of the residual the U-Net carves across the anneal,
    delta = beta_learned - beta_naive (blue = held back, red = driven ahead), for the
    slide. A single, large, crisp panel. Written as figures/fig_res_field.gif."""
    import matplotlib.animation as animation

    d = _res("coupling_ladder_data.npz")
    delta = d["delta"]
    mask, t = d["defect_mask"], d["t_norm"]
    vlim = float(d["vlim_d"])
    n = delta.shape[0]

    # Diverging blue -> neutral -> red, as asked: easy-blue negative, target-red positive.
    cmap = LinearSegmentedColormap.from_list("delta_rb", [EASY, "#eef0f1", TARGET])

    # constrained layout so the colorbar labels are never clipped by the frame edge
    # (animation.save writes at fixed figure size, with no tight-bbox rescue).
    fig, ax = plt.subplots(figsize=(6.1, 5.0), layout="constrained")
    # A gif has no alpha to spare, so paint the slide colour in directly.
    fig.patch.set_facecolor("#f1f1f1")

    im = ax.imshow(delta[0], origin="lower", cmap=cmap, vmin=-vlim, vmax=vlim,
                   interpolation="bicubic", animated=True)
    ax.contour(mask, levels=[0.5], colors="0.3", linewidths=1.1, alpha=0.85)
    ax.set_xticks([])
    ax.set_yticks([])
    ts.bare(ax, keep=())
    ttl = ax.set_title(rf"$\lambda = {t[0]:.2f}$", color=INK, fontsize=16, pad=10)

    cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2.5, width=0.8, labelsize=9.5, colors=INK)
    cb.set_ticks([-vlim, 0, vlim])
    cb.set_ticklabels([f"$-{vlim:.2f}$", "0", f"$+{vlim:.2f}$"])
    cb.set_label(r"$\beta_{\mathrm{learn}}-\beta_{\mathrm{naive}}$",
                 color=INK, fontsize=12)

    def update(i):
        im.set_data(delta[i])
        ttl.set_text(rf"$\lambda = {t[i]:.2f}$")
        return im, ttl

    anim = animation.FuncAnimation(fig, update, frames=n, interval=420, blit=False)
    out = Path(__file__).parent / "fig_res_field.gif"
    anim.save(out, writer="pillow", fps=2.6, dpi=150,
              savefig_kwargs=dict(facecolor="#f1f1f1"))
    plt.close(fig)
    print(f"  wrote {out.relative_to(Path(__file__).parent.parent)}")


# =============================================================================
FIGURES = {
    "fig02": fig02_critical_slowing_down,
    "fig03": fig03_ring_sectors,
    "fig04": fig04_annealing_family,
    "fig05": fig05_schedule_ticks,
    "defect": fig_defect_anneal,
    "pttower": fig_pt_tower,
    "fig07": fig07_fisher_metric,
    "fig08": fig08_2d_plane,
    "fig09": fig09_defect_lattice,
    "res_geometry": fig_res_geometry,
    "res_swaps": fig_res_swaps,
    "res_field": fig_res_field,
    "res_field_gif": fig_res_field_gif,
}


def main():
    ts.use()
    wanted = sys.argv[1:] or list(FIGURES)
    unknown = [w for w in wanted if w not in FIGURES]
    if unknown:
        sys.exit(f"unknown figure(s): {', '.join(unknown)}\nknown: {', '.join(FIGURES)}")

    for key in wanted:
        print(f"{key} ...")
        FIGURES[key]()
        if key == "fig02":
            _emit_fig02_overlay()  # slides 2 and 3 also need their animatable copies
        if key == "fig03":
            _emit_fig03_overlay()
        if key == "fig05":
            _emit_fig05_schedule()  # animated inline-SVG twin for the slide
    print(f"\n{len(wanted)} figure(s) written to figures/")


if __name__ == "__main__":
    main()

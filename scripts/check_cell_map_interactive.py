"""Headless smoke test for the interactive 12x8 cell map component.

Renders the generated HTML in Chromium, hovers a few grid cells and asserts the
side panel switches to the hovered cell. Run manually:

    python3 scripts/check_cell_map_interactive.py
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import xp_engine as xe  # noqa: E402
import xp_maps_interactive as xmi  # noqa: E402
import xp_study_engine as xpe  # noqa: E402

TOP_N = 250


def _pool():
    season = xe.load_european_league_season_passes()
    completed = season[season["is_won"] & season["has_end"]]
    counts = completed.groupby("player_id").size().sort_values(ascending=False)
    return completed[completed["player_id"].isin(counts.head(TOP_N).index)]


def main() -> int:
    from playwright.sync_api import sync_playwright

    analysis = xpe.build_cell_heatmap_analysis(_pool())
    html = xmi.build_cell_map_html(analysis)
    path = pathlib.Path(tempfile.mkdtemp()) / "cell_map.html"
    path.write_text(html, encoding="utf-8")

    cols = int(analysis["cols"])
    rows = int(analysis["rows"])
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 760})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(path.as_uri())
        page.wait_for_selector(".qp-title", timeout=30_000)
        page.wait_for_timeout(1500)

        if "Visão geral" not in page.inner_text(".qp-title"):
            failures.append(f"initial panel title unexpected: {page.inner_text('.qp-title')!r}")

        field_x = float(analysis["field_x"])
        field_y = float(analysis["field_y"])

        # Ask Plotly itself where a pitch coordinate lands: the axes are reversed
        # and domain-constrained, so the drag layer is not a linear stand-in.
        def cell_point(col: int, row: int) -> tuple[float, float]:
            pos = page.evaluate(
                """(p) => {
                    const gd = document.getElementById('qmap-plot');
                    const fl = gd._fullLayout;
                    const bb = gd.getBoundingClientRect();
                    return {
                        x: bb.left + fl.xaxis._offset + fl.xaxis.l2p(p[0]),
                        y: bb.top + fl.yaxis._offset + fl.yaxis.l2p(p[1]),
                    };
                }""",
                [(col + 0.5) * field_x / cols, (row + 0.5) * field_y / rows],
            )
            return pos["x"], pos["y"]

        def hover_cell(col: int, row: int) -> tuple[float, float]:
            x, y = cell_point(col, row)
            # A second nudge inside the same cell guarantees a fresh mousemove even
            # when the pointer was already parked on these coordinates.
            page.mouse.move(x, y, steps=4)
            page.mouse.move(x + 1, y + 1)
            page.wait_for_timeout(400)
            return x, y

        for col, row in ((5, 3), (9, 1), (2, 6)):
            hover_cell(col, row)
            title = page.inner_text(".qp-title")
            expected = f"C{col + 1}/L{row + 1}"
            if expected not in title:
                failures.append(f"hover ({col},{row}) -> panel {title!r}, expected {expected}")
            if not page.locator(".qp-row").count():
                failures.append(f"hover ({col},{row}) produced no destination rows")

        # Click pins the cell so later hovers must not change the panel.
        x, y = hover_cell(5, 3)
        page.mouse.click(x, y)
        page.wait_for_timeout(400)
        if not page.locator(".qp-pin").count():
            failures.append("click did not pin the cell")
        hover_cell(9, 6)
        if "C6/L4" not in page.inner_text(".qp-title"):
            failures.append("pinned cell changed on hover")

        page.click("#qmap-reset")
        page.wait_for_timeout(400)
        if "Visão geral" not in page.inner_text(".qp-title"):
            failures.append("reset did not restore the overall view")

        page.click('.qmap-btn[data-metric="volume"]')
        page.wait_for_timeout(400)
        page.click('.qmap-btn[data-scale="relative"]')
        page.wait_for_timeout(400)

        if errors:
            failures.append("JS errors: " + " | ".join(errors[:5]))
        browser.close()

    if failures:
        print("FAIL")
        for line in failures:
            print(" -", line)
        return 1
    print("OK — hover, pin, reset and toolbar toggles all behave")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

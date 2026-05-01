from __future__ import annotations

import json
import math
from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44.aedt"
DESIGN = "Array4_Diamond_D44"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"


def _values(sd, expr: str) -> list[float]:
    return [float(x) for x in sd.data_real(expr)]


def _axis_values(sd, axis: str) -> list[float]:
    vals = []
    for raw in sd.intrinsics.get(axis, []):
        text = str(raw).replace("deg", "")
        vals.append(float(text))
    return vals


def evaluate(hfss: Hfss, freq_ghz: float = 8.0) -> dict:
    expr = "dB(GainTotal)"
    ar_expr = "AxialRatioValue"
    sd = hfss.post.get_solution_data(
        expressions=[expr, ar_expr],
        setup_sweep_name=SOLUTION,
        domain="Sweep",
        variations={"Freq": [f"{freq_ghz:g}GHz"], "Theta": ["All"], "Phi": ["All"]},
        primary_sweep_variable="Phi",
        report_category="Far Fields",
        context=SPHERE,
    )
    theta_vals = _axis_values(sd, "Theta")
    phi_vals = _axis_values(sd, "Phi")
    gains = _values(sd, expr)
    ars = _values(sd, ar_expr)

    rows = []
    ntheta = len(theta_vals)
    nphi = len(phi_vals)
    if len(gains) != ntheta * nphi:
        raise RuntimeError(
            f"Unexpected far-field grid: {len(gains)} points, Theta={ntheta}, Phi={nphi}"
        )

    idx = 0
    for phi in phi_vals:
        for theta in theta_vals:
            rows.append({"theta": theta, "phi": phi, "gain": gains[idx], "ar": ars[idx]})
            idx += 1

    roi = [r for r in rows if 0.0 <= r["theta"] <= 360.0 and 45.0 <= r["phi"] <= 90.0]
    min_row = min(roi, key=lambda r: r["gain"])
    max_row = max(roi, key=lambda r: r["gain"])
    ar_min = min(roi, key=lambda r: r["ar"])
    ar_max = max(roi, key=lambda r: r["ar"])
    return {
        "freq_ghz": freq_ghz,
        "theta_count": ntheta,
        "phi_count": nphi,
        "fov": "Theta 0-360 deg, Phi 45-90 deg",
        "gain_min_dbi": min_row["gain"],
        "gain_max_dbi": max_row["gain"],
        "gain_ripple_db": max_row["gain"] - min_row["gain"],
        "gain_min_point": min_row,
        "gain_max_point": max_row,
        "axial_ratio_min": ar_min["ar"],
        "axial_ratio_max": ar_max["ar"],
    }


def main() -> None:
    lock = PROJECT_PATH.with_suffix(".aedt.lock")
    if lock.exists():
        try:
            lock.unlink()
        except OSError:
            pass

    hfss = Hfss(
        project=str(PROJECT_PATH),
        design=DESIGN,
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    try:
        sources = hfss.get_all_sources()
        results = {}
        source_sets: dict[str, dict[str, tuple[float, float]]] = {
            "default": {},
        }
        for source in sources:
            source_sets[f"{source}_only"] = {
                src: (1.0 if src == source else 0.0, 0.0) for src in sources
            }
        for name, assignments in source_sets.items():
            if assignments:
                hfss.edit_sources(assignments)
            results[name] = evaluate(hfss)
        out = ROOT / "reports_d44" / "UWB_CH9_D44_fov_source_metrics.json"
        out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps(results, indent=2))
        print(f"Wrote {out}")
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


if __name__ == "__main__":
    main()

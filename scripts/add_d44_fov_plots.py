from __future__ import annotations

from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_FOV.aedt"
DESIGN = "Array4_Diamond_D44_FOV"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"


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
        hfss.edit_sources({src: (1.0 if src == "P1" else 0.0, 0.0) for src in sources})
        variations = {"Freq": ["7.9855GHz"], "Theta": ["All"], "Phi": ["All"]}
        hfss.post.create_report(
            expressions=["dB(GainTotal)"],
            setup_sweep_name=SOLUTION,
            report_category="Far Fields",
            context=SPHERE,
            plot_type="3D Polar Plot",
            plot_name="FOV_3D_P1_GainTotal_7p9855GHz",
            variations=variations,
        )
        hfss.post.create_report(
            expressions=["dB(GainTotal)"],
            setup_sweep_name=SOLUTION,
            report_category="Far Fields",
            context=SPHERE,
            plot_type="Radiation Pattern",
            plot_name="FOV_Polar_P1_GainTotal_7p9855GHz",
            variations=variations,
            primary_sweep_variable="Theta",
        )
        hfss.save_project()
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


if __name__ == "__main__":
    main()

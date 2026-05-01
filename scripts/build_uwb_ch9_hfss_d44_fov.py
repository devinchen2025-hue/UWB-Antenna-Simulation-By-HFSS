from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_FOV.aedt"
PARAM_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_FOV_params.json"
RESULTS_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_FOV.aedtresults"
PYAEDT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_FOV.pyaedt"


PARAMS = {
    "freq_center_ghz": 8.0,
    "freq_start_ghz": 7.7,
    "freq_stop_ghz": 8.3,
    "freq_step_ghz": 0.02,
    "target_start_ghz": 7.738,
    "target_stop_ghz": 8.233,
    "element_spacing_mm": 17.0,
    "board_diameter_mm": 44.0,
    "substrate_h_mm": 0.508,
    "copper_t_mm": 0.035,
    "epsr": 3.48,
    "tan_delta": 0.0037,
    "ground_radius_mm": 13.0,
    "monopole_height_mm": 8.6,
    "monopole_radius_mm": 0.28,
    "top_hat_radius_mm": 1.55,
    "feed_pad_radius_mm": 0.85,
    "port_width_mm": 1.0,
    "parasitic_sleeve_enabled": 0.0,
    "sleeve_radius_mm": 1.15,
    "sleeve_height_mm": 4.2,
    "sleeve_wire_radius_mm": 0.12,
    "air_frequency_ghz": 7.0,
}


ELEMENTS = [
    ("E1", 0.0),
    ("E2", 90.0),
    ("E3", 180.0),
    ("E4", 270.0),
]


def local_basis(angle_deg: float) -> tuple[tuple[float, float], tuple[float, float]]:
    a = math.radians(angle_deg)
    radial = (math.cos(a), math.sin(a))
    tangential = (-math.sin(a), math.cos(a))
    return radial, tangential


def polygon_sheet(hfss: Hfss, name: str, points: list[list[float]], material: str | None = None):
    return hfss.modeler.create_polyline(
        points,
        cover_surface=True,
        close_surface=True,
        name=name,
        material=material,
    )


def add_ro4350b(hfss: Hfss, params: dict) -> str:
    mat_name = "RO4350B_custom_D44_FOV"
    if mat_name not in hfss.materials.material_keys:
        mat = hfss.materials.add_material(mat_name)
        mat.permittivity = params["epsr"]
        mat.dielectric_loss_tangent = params["tan_delta"]
    return mat_name


def add_lumped_port_sheet(
    hfss: Hfss,
    name: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
) -> str:
    cx, cy = center
    h = params["substrate_h_mm"]
    half_w = params["port_width_mm"] / 2.0
    _, tangential = local_basis(angle_deg)
    tx, ty = tangential
    p0 = [cx - half_w * tx, cy - half_w * ty, 0.0]
    p1 = [cx + half_w * tx, cy + half_w * ty, 0.0]
    p2 = [cx + half_w * tx, cy + half_w * ty, h]
    p3 = [cx - half_w * tx, cy - half_w * ty, h]
    port_sheet = polygon_sheet(hfss, f"{name}_lumped_port_sheet", [p0, p1, p2, p3], None)
    hfss.lumped_port(
        port_sheet.name,
        create_port_sheet=False,
        integration_line=[[cx, cy, h], [cx, cy, 0.0]],
        impedance=50,
        name=f"P{name[-1]}",
        renormalize=True,
    )
    return port_sheet.name


def add_parasitic_sleeve(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    params: dict,
) -> list[str]:
    if params.get("parasitic_sleeve_enabled", 0.0) < 0.5:
        return []

    cx, cy = center
    h = params["substrate_h_mm"]
    sleeve_r = params["sleeve_radius_mm"]
    wire_r = params["sleeve_wire_radius_mm"]
    sleeve_h = params["sleeve_height_mm"]
    names = []
    for idx, ang in enumerate([45.0, 135.0, 225.0, 315.0], start=1):
        x = cx + sleeve_r * math.cos(math.radians(ang))
        y = cy + sleeve_r * math.sin(math.radians(ang))
        wire = hfss.modeler.create_cylinder(
            "Z",
            [x, y, h],
            wire_r,
            sleeve_h,
            num_sides=12,
            name=f"{tag}_sleeve_post_{idx}",
            material="copper",
        )
        names.append(wire.name)

    top_points = []
    bottom_points = []
    for i in range(48):
        a = 2.0 * math.pi * i / 48
        top_points.append([cx + sleeve_r * math.cos(a), cy + sleeve_r * math.sin(a), h + sleeve_h])
        bottom_points.append([cx + sleeve_r * math.cos(a), cy + sleeve_r * math.sin(a), h])
    top_ring = hfss.modeler.create_polyline(
        top_points,
        cover_surface=False,
        close_surface=True,
        name=f"{tag}_sleeve_top_ring",
        material="copper",
        xsection_type="Circle",
        xsection_width=2.0 * wire_r,
        xsection_num_seg=12,
    )
    bottom_ring = hfss.modeler.create_polyline(
        bottom_points,
        cover_surface=False,
        close_surface=True,
        name=f"{tag}_sleeve_bottom_ring",
        material="copper",
        xsection_type="Circle",
        xsection_width=2.0 * wire_r,
        xsection_num_seg=12,
    )
    names.extend([top_ring.name, bottom_ring.name])
    return names


def add_vertical_element(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
) -> tuple[list[str], str]:
    cx, cy = center
    h = params["substrate_h_mm"]
    monopole_h = params["monopole_height_mm"]
    monopole_r = params["monopole_radius_mm"]
    feed_pad_r = params["feed_pad_radius_mm"]
    top_hat_r = params["top_hat_radius_mm"]

    names = []
    feed_pad = hfss.modeler.create_circle(
        "XY",
        [cx, cy, h],
        feed_pad_r,
        num_sides=48,
        name=f"{tag}_feed_pad",
        material="copper",
    )
    names.append(feed_pad.name)

    monopole = hfss.modeler.create_cylinder(
        "Z",
        [cx, cy, h],
        monopole_r,
        monopole_h,
        num_sides=24,
        name=f"{tag}_vertical_monopole",
        material="copper",
    )
    names.append(monopole.name)

    top_hat = hfss.modeler.create_circle(
        "XY",
        [cx, cy, h + monopole_h],
        top_hat_r,
        num_sides=48,
        name=f"{tag}_capacitive_hat",
        material="copper",
    )
    names.append(top_hat.name)

    names.extend(add_parasitic_sleeve(hfss, tag, center, params))
    port_sheet = add_lumped_port_sheet(hfss, tag, center, angle_deg, params)
    return names, port_sheet


def create_reports(hfss: Hfss, setup_name: str, sweep_name: str):
    solution = f"{setup_name} : {sweep_name}"
    try:
        hfss.post.create_report(
            expressions=hfss.get_traces_for_plot(category="dB(S"),
            setup_sweep_name=solution,
            report_category="Modal Solution Data",
            plot_name="FOV_S_Parameters",
        )
    except Exception as exc:
        print(f"Report creation deferred: {exc}", flush=True)

    try:
        hfss.post.create_report(
            expressions=["dB(GainTotal)"],
            setup_sweep_name=solution,
            report_category="Far Fields",
            context="Upper_Hemisphere_5deg",
            plot_type="3D Polar Plot",
            plot_name="FOV_3D_GainTotal_8GHz",
            variations={"Freq": ["8GHz"], "Theta": ["All"], "Phi": ["All"]},
        )
    except Exception as exc:
        print(f"Far-field report creation deferred: {exc}", flush=True)


def clean_previous_outputs() -> None:
    for generated_path in [RESULTS_PATH, PYAEDT_PATH, PROJECT_PATH.with_suffix(".aedt.lock")]:
        if generated_path.exists():
            if generated_path.is_dir():
                shutil.rmtree(generated_path, ignore_errors=True)
            else:
                try:
                    generated_path.unlink()
                except OSError:
                    pass

    if PROJECT_PATH.exists():
        backup = PROJECT_PATH.with_suffix(".previous.aedt")
        try:
            if backup.exists():
                backup.unlink()
            PROJECT_PATH.replace(backup)
        except OSError:
            pass


def build_project(
    analyze: bool = False,
    non_graphical: bool = False,
    quick: bool = False,
    band_samples: bool = False,
) -> Path:
    print("Stage: starting D44_FOV AEDT/project build", flush=True)
    clean_previous_outputs()

    hfss = Hfss(
        project=str(PROJECT_PATH),
        design="Array4_Diamond_D44_FOV",
        solution_type="DrivenModal",
        version="2023.1",
        non_graphical=non_graphical,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    hfss.modeler.model_units = "mm"

    substrate_material = add_ro4350b(hfss, PARAMS)
    board_radius = PARAMS["board_diameter_mm"] / 2.0
    h = PARAMS["substrate_h_mm"]
    d = PARAMS["element_spacing_mm"]
    center_radius = d / math.sqrt(2.0)

    substrate = hfss.modeler.create_cylinder(
        "Z",
        [0, 0, 0],
        board_radius,
        h,
        num_sides=128,
        name="D44_FOV_RO4350B_circular_substrate",
        material=substrate_material,
    )
    substrate.transparency = 0.65

    ground = hfss.modeler.create_circle(
        "XY",
        [0, 0, 0],
        PARAMS["ground_radius_mm"],
        num_sides=128,
        name="D44_FOV_bottom_ground",
        material="copper",
    )
    print("Stage: substrate and circular ground created", flush=True)

    sheet_metals = [ground.name]
    solid_metals = []
    port_sheets = []
    for tag, angle in ELEMENTS:
        cx = center_radius * math.cos(math.radians(angle))
        cy = center_radius * math.sin(math.radians(angle))
        metals, port_sheet = add_vertical_element(hfss, tag, (cx, cy), angle, PARAMS)
        for name in metals:
            if "monopole" in name or "sleeve_post" in name or "sleeve_ring" in name:
                solid_metals.append(name)
            else:
                sheet_metals.append(name)
        port_sheets.append(port_sheet)
    print("Stage: four vertical quasi-omni elements and lumped ports created", flush=True)

    hfss.assign_perfecte_to_sheets(sheet_metals, name="D44_FOV_PEC_sheets", is_infinite_ground=False)
    print("Stage: PEC sheet boundaries created", flush=True)

    hfss.create_open_region(
        frequency=f"{PARAMS['air_frequency_ghz']}GHz",
        boundary="Radiation",
        apply_infinite_ground=False,
    )
    hfss.insert_infinite_sphere(
        theta_start=0,
        theta_stop=90,
        theta_step=5,
        phi_start=0,
        phi_stop=360,
        phi_step=5,
        name="Upper_Hemisphere_5deg",
    )
    print("Stage: radiation region and upper-hemisphere sphere created", flush=True)

    setup = hfss.create_setup(
        name="Setup_CH9",
        setup_type="HFSSDriven",
        Frequency=f"{PARAMS['freq_center_ghz']}GHz",
        MaximumPasses=4 if quick else 7,
        MinimumPasses=1 if quick else 2,
        MaxDeltaS=0.04 if quick else 0.02,
        BasisOrder=1,
        PercentRefinement=30,
    )
    if quick:
        if band_samples:
            sweep = hfss.create_linear_count_sweep(
                setup=setup.name,
                unit="GHz",
                start_frequency=PARAMS["target_start_ghz"],
                stop_frequency=PARAMS["target_stop_ghz"],
                num_of_freq_points=3,
                name="Sweep_CH9",
                save_fields=True,
                save_rad_fields=True,
                sweep_type="Discrete",
            )
        else:
            sweep = hfss.create_single_point_sweep(
                setup=setup.name,
                unit="GHz",
                freq=PARAMS["freq_center_ghz"],
                name="Sweep_CH9",
                save_single_field=True,
                save_fields=True,
                save_rad_fields=True,
            )
    else:
        sweep = hfss.create_linear_step_sweep(
            setup=setup.name,
            unit="GHz",
            start_frequency=PARAMS["freq_start_ghz"],
            stop_frequency=PARAMS["freq_stop_ghz"],
            step_size=PARAMS["freq_step_ghz"],
            name="Sweep_CH9",
            save_fields=True,
            save_rad_fields=True,
            sweep_type="Discrete",
        )
    print("Stage: setup and sweep created", flush=True)

    create_reports(hfss, setup.name, sweep.name)
    print("Stage: report definitions created", flush=True)

    notes = {
        "project": str(PROJECT_PATH),
        "design": hfss.design_name,
        "model": "D44 FOV variant with four top-loaded vertical monopole elements in a diamond layout.",
        "pcb_constraint": "Circular PCB, diameter 44 mm.",
        "fov_target": "Theta 0-360 deg, Phi 45-90 deg, GainTotal min >= -5 dBi, donut-like pattern.",
        "element_centers_mm": {
            tag: [
                round(center_radius * math.cos(math.radians(angle)), 6),
                round(center_radius * math.sin(math.radians(angle)), 6),
            ]
            for tag, angle in ELEMENTS
        },
        "nearest_neighbor_spacing_mm": PARAMS["element_spacing_mm"],
        "ports": ["P1", "P2", "P3", "P4"],
        "parameters": PARAMS,
        "notes": [
            "This variant prioritizes upper-horizon FOV coverage and donut-shaped radiation.",
            "Each element is a lumped-port-fed vertical monopole with a small capacitive top hat.",
            "For PDOA receive operation, inspect per-port patterns and the four-port coverage envelope rather than only equal-phase combined excitation.",
        ],
    }
    PARAM_PATH.write_text(json.dumps(notes, indent=2), encoding="utf-8")

    hfss.save_project()
    print("Stage: D44_FOV project saved", flush=True)

    if analyze:
        print("Stage: D44_FOV analysis started", flush=True)
        ok = hfss.analyze_setup(setup.name, cores=4, tasks=4, blocking=True)
        print(f"Analyze result: {ok}", flush=True)
        hfss.save_project()
        print("Stage: solved D44_FOV project saved", flush=True)

    hfss.release_desktop(close_projects=False, close_desktop=non_graphical)
    return PROJECT_PATH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true", help="Run HFSS solve after building the model.")
    parser.add_argument("--non-graphical", action="store_true", help="Launch AEDT in non-graphical mode.")
    parser.add_argument("--quick", action="store_true", help="Use fast single-point style sweep for FOV tuning.")
    parser.add_argument(
        "--band-samples",
        action="store_true",
        help="In quick mode, solve target start, center, and target stop frequencies.",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Override a numeric design parameter, for example --param monopole_height_mm=8.8.",
    )
    args = parser.parse_args()
    for item in args.param:
        key, value = item.split("=", 1)
        PARAMS[key] = float(value)
    path = build_project(
        analyze=args.analyze,
        non_graphical=args.non_graphical,
        quick=args.quick,
        band_samples=args.band_samples,
    )
    print(path)


if __name__ == "__main__":
    main()

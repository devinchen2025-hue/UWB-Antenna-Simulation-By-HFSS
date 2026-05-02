from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.aedt"
PARAM_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP_params.json"
RESULTS_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.aedtresults"
PYAEDT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.pyaedt"


PARAMS = {
    "freq_center_ghz": 8.0,
    "freq_start_ghz": 7.7,
    "freq_stop_ghz": 8.3,
    "freq_step_ghz": 0.02,
    "target_start_ghz": 7.738,
    "target_stop_ghz": 8.233,
    "element_spacing_mm": 17.0,
    "board_diameter_mm": 44.0,
    "total_height_limit_mm": 8.0,
    "substrate_h_mm": 2.0,
    "copper_t_mm": 0.035,
    "epsr": 3.48,
    "tan_delta": 0.0037,
    "ground_radius_mm": 21.4,
    "patch_side_mm": 8.91,
    "corner_cut_mm": 0.62,
    "feed_offset_u_mm": 2.68,
    "feed_offset_v_mm": 0.0,
    "feed_pad_radius_mm": 0.45,
    "port_width_mm": 0.75,
    "via_antipad_radius_mm": 0.9,
    "isolation_slot_enabled": 1.0,
    "isolation_slot_length_mm": 8.0,
    "isolation_slot_width_mm": 0.35,
    "isolation_slot_inner_mm": 3.2,
    "air_frequency_ghz": 7.0,
    "cp_axial_ratio_target_db": 3.0,
    "fov_min_gain_target_dbi": -5.0,
}


ELEMENTS = [
    ("E1", 0.0),
    ("E2", 90.0),
    ("E3", 180.0),
    ("E4", 270.0),
]


def local_to_global(cx: float, cy: float, angle_deg: float, u: float, v: float, z: float) -> list[float]:
    a = math.radians(angle_deg)
    eu = (math.cos(a), math.sin(a))
    ev = (-math.sin(a), math.cos(a))
    return [cx + u * eu[0] + v * ev[0], cy + u * eu[1] + v * ev[1], z]


def polygon_sheet(hfss: Hfss, name: str, points: list[list[float]], material: str | None = "copper"):
    return hfss.modeler.create_polyline(
        points,
        cover_surface=True,
        close_surface=True,
        name=name,
        material=material,
    )


def rectangle_points(
    cx: float,
    cy: float,
    angle_deg: float,
    u_min: float,
    u_max: float,
    v_min: float,
    v_max: float,
    z: float,
) -> list[list[float]]:
    return [
        local_to_global(cx, cy, angle_deg, u_min, v_min, z),
        local_to_global(cx, cy, angle_deg, u_max, v_min, z),
        local_to_global(cx, cy, angle_deg, u_max, v_max, z),
        local_to_global(cx, cy, angle_deg, u_min, v_max, z),
    ]


def add_ro4350b(hfss: Hfss, params: dict) -> str:
    mat_name = "RO4350B_custom_D44_H8_CP"
    if mat_name not in hfss.materials.material_keys:
        mat = hfss.materials.add_material(mat_name)
        mat.permittivity = params["epsr"]
        mat.dielectric_loss_tangent = params["tan_delta"]
    return mat_name


def cp_patch_points(
    cx: float,
    cy: float,
    angle_deg: float,
    params: dict,
) -> list[list[float]]:
    half = params["patch_side_mm"] / 2.0
    cut = params["corner_cut_mm"]
    h = params["substrate_h_mm"]
    local = [
        (-half + cut, -half),
        (half, -half),
        (half, half - cut),
        (half - cut, half),
        (-half, half),
        (-half, -half + cut),
    ]
    return [local_to_global(cx, cy, angle_deg, u, v, h) for u, v in local]


def add_lumped_feed(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
) -> tuple[list[str], str]:
    cx, cy = center
    h = params["substrate_h_mm"]
    feed_u = params["feed_offset_u_mm"]
    feed_v = params["feed_offset_v_mm"]
    feed = local_to_global(cx, cy, angle_deg, feed_u, feed_v, h)
    base = local_to_global(cx, cy, angle_deg, feed_u, feed_v, 0.0)
    feed_pad = hfss.modeler.create_circle(
        "XY",
        feed,
        params["feed_pad_radius_mm"],
        num_sides=36,
        name=f"{tag}_feed_pad",
        material="copper",
    )

    half_w = params["port_width_mm"] / 2.0
    p0 = local_to_global(cx, cy, angle_deg, feed_u, feed_v - half_w, 0.0)
    p1 = local_to_global(cx, cy, angle_deg, feed_u, feed_v + half_w, 0.0)
    p2 = local_to_global(cx, cy, angle_deg, feed_u, feed_v + half_w, h)
    p3 = local_to_global(cx, cy, angle_deg, feed_u, feed_v - half_w, h)
    port_sheet = polygon_sheet(hfss, f"{tag}_probe_lumped_port_sheet", [p0, p1, p2, p3], None)
    hfss.lumped_port(
        port_sheet.name,
        create_port_sheet=False,
        integration_line=[feed, base],
        impedance=50,
        name=f"P{tag[-1]}",
        renormalize=True,
    )
    return [feed_pad.name], port_sheet.name


def add_cp_patch_element(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
) -> tuple[list[str], str]:
    patch = polygon_sheet(hfss, f"{tag}_corner_truncated_cp_patch", cp_patch_points(*center, angle_deg, params))
    feed_names, port_sheet = add_lumped_feed(hfss, tag, center, angle_deg, params)
    return [patch.name, *feed_names], port_sheet


def add_isolation_slots(hfss: Hfss, params: dict) -> list[str]:
    if params.get("isolation_slot_enabled", 0.0) < 0.5:
        return []

    z = 0.0
    names = []
    inner = params["isolation_slot_inner_mm"]
    length = params["isolation_slot_length_mm"]
    width = params["isolation_slot_width_mm"]
    for idx, angle in enumerate([45.0, 135.0, 225.0, 315.0], start=1):
        pts = rectangle_points(0.0, 0.0, angle, inner, inner + length, -width / 2.0, width / 2.0, z)
        slot = polygon_sheet(hfss, f"ground_isolation_slot_{idx}", pts, "vacuum")
        names.append(slot.name)
    return names


def create_reports(hfss: Hfss, setup_name: str, sweep_name: str):
    solution = f"{setup_name} : {sweep_name}"
    try:
        hfss.post.create_report(
            expressions=hfss.get_traces_for_plot(category="dB(S"),
            setup_sweep_name=solution,
            report_category="Modal Solution Data",
            plot_name="H8_PCB_CP_S_Parameters",
        )
    except Exception as exc:
        print(f"S-parameter report creation deferred: {exc}", flush=True)

    for expression, name in [
        ("dB(GainTotal)", "H8_PCB_CP_3D_GainTotal_8GHz"),
        ("AxialRatioValue", "H8_PCB_CP_3D_AxialRatio_8GHz"),
    ]:
        try:
            hfss.post.create_report(
                expressions=[expression],
                setup_sweep_name=solution,
                report_category="Far Fields",
                context="Upper_Hemisphere_5deg",
                plot_type="3D Polar Plot",
                plot_name=name,
                variations={"Freq": ["8GHz"], "Theta": ["All"], "Phi": ["All"]},
            )
        except Exception as exc:
            print(f"Far-field report creation deferred for {expression}: {exc}", flush=True)


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


def validate_params(params: dict) -> None:
    total_h = params["substrate_h_mm"] + 2.0 * params["copper_t_mm"]
    if total_h > params["total_height_limit_mm"]:
        raise ValueError(
            f"Total PCB antenna height {total_h:.3f} mm exceeds "
            f"{params['total_height_limit_mm']:.3f} mm."
        )
    if params["ground_radius_mm"] > params["board_diameter_mm"] / 2.0:
        raise ValueError("Ground radius must stay inside the circular PCB.")
    max_patch_radius = params["element_spacing_mm"] / math.sqrt(2.0) + params["patch_side_mm"] / math.sqrt(2.0)
    board_radius = params["board_diameter_mm"] / 2.0
    if max_patch_radius > board_radius - 0.4:
        raise ValueError("Patch corner is too close to or outside the 44 mm board edge.")


def build_project(
    analyze: bool = False,
    non_graphical: bool = False,
    quick: bool = False,
    band_samples: bool = False,
    sparam_only: bool = False,
) -> Path:
    validate_params(PARAMS)
    print("Stage: starting D44_H8_PCB_CP AEDT/project build", flush=True)
    clean_previous_outputs()

    hfss = Hfss(
        project=str(PROJECT_PATH),
        design="Array4_Diamond_D44_H8_PCB_CP",
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
    center_radius = PARAMS["element_spacing_mm"] / math.sqrt(2.0)

    substrate = hfss.modeler.create_cylinder(
        "Z",
        [0, 0, 0],
        board_radius,
        h,
        num_sides=128,
        name="D44_H8_CP_RO4350B_circular_substrate",
        material=substrate_material,
    )
    substrate.transparency = 0.65

    ground = hfss.modeler.create_circle(
        "XY",
        [0, 0, 0],
        PARAMS["ground_radius_mm"],
        num_sides=128,
        name="D44_H8_CP_bottom_ground",
        material="copper",
    )
    metal_names = [ground.name]
    print("Stage: substrate and circular ground created", flush=True)

    slot_names = add_isolation_slots(hfss, PARAMS)
    if slot_names:
        try:
            hfss.modeler.subtract(ground.name, slot_names, keep_originals=False)
            print("Stage: bottom-ground isolation slots cut", flush=True)
        except Exception as exc:
            print(f"Isolation slot subtraction deferred/failed: {exc}", flush=True)

    port_sheets = []
    for tag, angle in ELEMENTS:
        cx = center_radius * math.cos(math.radians(angle))
        cy = center_radius * math.sin(math.radians(angle))
        metals, port_sheet = add_cp_patch_element(hfss, tag, (cx, cy), angle, PARAMS)
        metal_names.extend(metals)
        port_sheets.append(port_sheet)
    print("Stage: four corner-truncated PCB CP patch elements and lumped feeds created", flush=True)

    hfss.assign_perfecte_to_sheets(metal_names, name="D44_H8_PCB_CP_PEC_metallization", is_infinite_ground=False)
    print("Stage: metallization PEC boundaries created", flush=True)

    hfss.create_open_region(
        frequency=f"{PARAMS['air_frequency_ghz']}GHz",
        boundary="Radiation",
        apply_infinite_ground=False,
    )
    if not sparam_only:
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
    else:
        print("Stage: S-parameter-only mode skips far-field sphere creation", flush=True)

    max_passes = 4 if quick else 5 if sparam_only else 7
    min_passes = 1 if quick or sparam_only else 2
    max_delta_s = 0.05 if quick else 0.03 if sparam_only else 0.02
    setup = hfss.create_setup(
        name="Setup_CH9",
        setup_type="HFSSDriven",
        Frequency=f"{PARAMS['freq_center_ghz']}GHz",
        MaximumPasses=max_passes,
        MinimumPasses=min_passes,
        MaxDeltaS=max_delta_s,
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
                save_fields=not sparam_only,
                save_rad_fields=not sparam_only,
                sweep_type="Discrete",
            )
        else:
            sweep = hfss.create_single_point_sweep(
                setup=setup.name,
                unit="GHz",
                freq=PARAMS["freq_center_ghz"],
                name="Sweep_CH9",
                save_single_field=not sparam_only,
                save_fields=not sparam_only,
                save_rad_fields=not sparam_only,
            )
    else:
        sweep = hfss.create_linear_step_sweep(
            setup=setup.name,
            unit="GHz",
            start_frequency=PARAMS["freq_start_ghz"],
            stop_frequency=PARAMS["freq_stop_ghz"],
            step_size=PARAMS["freq_step_ghz"],
            name="Sweep_CH9",
            save_fields=not sparam_only,
            save_rad_fields=not sparam_only,
            sweep_type="Discrete",
        )
    print("Stage: setup and sweep created", flush=True)

    if not sparam_only:
        create_reports(hfss, setup.name, sweep.name)
        print("Stage: report definitions created", flush=True)

    total_height = PARAMS["substrate_h_mm"] + 2.0 * PARAMS["copper_t_mm"]
    notes = {
        "project": str(PROJECT_PATH),
        "design": hfss.design_name,
        "model": "D44 H<=8 mm PCB-printable circular-polarization candidate using four single-feed corner-truncated square patches.",
        "pcb_constraint": "Circular PCB, diameter 44 mm.",
        "height_constraint": f"PCB + copper height {total_height:.3f} mm <= {PARAMS['total_height_limit_mm']} mm.",
        "manufacturing_intent": [
            "No vertical monopole, top hat, or post-loaded radiator is required.",
            "The antenna is intended as a standard double-sided PCB: top CP patches, bottom ground, and probe/lumped feed locations.",
            "The starting stackup uses 2.0 mm RO4350B-like material for more bandwidth while staying far below the 8 mm envelope.",
            "The default patch/feed dimensions are the best quick-sweep S-parameter candidate found in this branch.",
        ],
        "cp_target": "AxialRatioValue <= 3 dB in the selected FOV and CH9 frequencies.",
        "fov_target": "Theta 0-360 deg, Phi 45-90 deg, GainTotal min >= -5 dBi.",
        "element_centers_mm": {
            tag: [
                round(center_radius * math.cos(math.radians(angle)), 6),
                round(center_radius * math.sin(math.radians(angle)), 6),
            ]
            for tag, angle in ELEMENTS
        },
        "nearest_neighbor_spacing_mm": PARAMS["element_spacing_mm"],
        "ports": ["P1", "P2", "P3", "P4"],
        "source_guidance": [
            "Inspect per-port source contexts for PDOA receive operation.",
            "Use sequential quadrature all-port excitation only as an array CP sanity check, not as the PDOA single-channel coverage signoff.",
        ],
        "parameters": PARAMS,
    }
    PARAM_PATH.write_text(json.dumps(notes, indent=2), encoding="utf-8")

    hfss.save_project()
    print("Stage: D44_H8_PCB_CP project saved", flush=True)

    if analyze:
        print("Stage: D44_H8_PCB_CP analysis started", flush=True)
        ok = hfss.analyze_setup(setup.name, cores=4, tasks=4, blocking=True)
        print(f"Analyze result: {ok}", flush=True)
        hfss.save_project()
        print("Stage: solved D44_H8_PCB_CP project saved", flush=True)

    hfss.release_desktop(close_projects=False, close_desktop=non_graphical)
    return PROJECT_PATH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true", help="Run HFSS solve after building the model.")
    parser.add_argument("--non-graphical", action="store_true", help="Launch AEDT in non-graphical mode.")
    parser.add_argument("--quick", action="store_true", help="Use a faster quick-tuning setup.")
    parser.add_argument("--band-samples", action="store_true", help="In quick mode, solve target start, center, and target stop frequencies.")
    parser.add_argument("--sparam-only", action="store_true", help="Skip far fields and save only S-parameter data.")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Override a numeric design parameter, for example --param patch_side_mm=9.6.",
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
        sparam_only=args.sparam_only,
    )
    print(path)


if __name__ == "__main__":
    main()

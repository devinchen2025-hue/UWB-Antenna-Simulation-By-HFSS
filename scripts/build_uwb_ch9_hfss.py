from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array.aedt"
PARAM_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_params.json"
RESULTS_PATH = ROOT / "UWB_CH9_Diamond_CP_Array.aedtresults"
PYAEDT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array.pyaedt"


PARAMS = {
    "freq_center_ghz": 8.0,
    "freq_start_ghz": 7.5,
    "freq_stop_ghz": 8.5,
    "freq_step_ghz": 0.02,
    "target_start_ghz": 7.738,
    "target_stop_ghz": 8.233,
    "element_spacing_mm": 17.0,
    "board_side_mm": 70.0,
    "substrate_h_mm": 0.508,
    "copper_t_mm": 0.035,
    "epsr": 3.48,
    "tan_delta": 0.0037,
    "patch_l_mm": 10.55,
    "corner_cut_mm": 0.92,
    "disc_radius_mm": 4.6,
    "feed_w_mm": 1.10,
    "inset_depth_mm": 3.10,
    "notch_gap_mm": 0.28,
    "partial_ground_w_mm": 10.0,
    "partial_ground_gap_mm": 0.8,
    "iso_vias_enabled": 0.0,
    "iso_walls_enabled": 0.0,
    "iso_wall_len_mm": 7.2,
    "iso_wall_start_mm": 0.8,
    "ebg_via_radius_mm": 0.16,
    "ebg_pitch_mm": 3.0,
    "ebg_ring_radius_mm": 8.1,
    "air_frequency_ghz": 7.0,
}


ELEMENTS = [
    ("E1", 0.0),
    ("E2", 90.0),
    ("E3", 180.0),
    ("E4", 270.0),
]


def local_to_global(cx: float, cy: float, angle_deg: float, u: float, v: float, z: float) -> list[float]:
    """Map element-local coordinates to global model coordinates."""
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


def add_ro4350b(hfss: Hfss) -> str:
    mat_name = "RO4350B_custom"
    if mat_name not in hfss.materials.material_keys:
        mat = hfss.materials.add_material(mat_name)
        mat.permittivity = PARAMS["epsr"]
        mat.dielectric_loss_tangent = PARAMS["tan_delta"]
    return mat_name


def add_cp_patch_element(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
) -> tuple[list[str], str]:
    """Create one microstrip-fed UWB planar monopole element.

    The element uses a radial feed line, circular radiator, and local partial
    ground. This topology is much better suited to UWB and azimuth coverage than
    a high-Q full-ground patch while still being a planar microstrip-fed antenna.
    """
    cx, cy = center
    h = params["substrate_h_mm"]
    feed_w = params["feed_w_mm"]
    radius = params["disc_radius_mm"]
    ground_w = params["partial_ground_w_mm"]
    ground_gap = params["partial_ground_gap_mm"]
    board_half = params["board_side_mm"] / 2.0
    r = params["element_spacing_mm"] / math.sqrt(2.0)
    u_port = board_half - r

    disc = hfss.modeler.create_circle(
        "XY",
        [cx, cy, h],
        radius,
        num_sides=72,
        name=f"{tag}_disc",
        material="copper",
    )
    feed_overlap_u = -0.35 * radius
    feed_points = [
        local_to_global(cx, cy, angle_deg, feed_overlap_u, -feed_w / 2.0, h),
        local_to_global(cx, cy, angle_deg, u_port, -feed_w / 2.0, h),
        local_to_global(cx, cy, angle_deg, u_port, feed_w / 2.0, h),
        local_to_global(cx, cy, angle_deg, feed_overlap_u, feed_w / 2.0, h),
    ]
    feed = polygon_sheet(hfss, f"{tag}_feed_line", feed_points)

    u_ground_inner = radius + ground_gap
    local_ground = [
        (u_ground_inner, -ground_w / 2.0),
        (u_port, -ground_w / 2.0),
        (u_port, ground_w / 2.0),
        (u_ground_inner, ground_w / 2.0),
    ]
    ground_points = [local_to_global(cx, cy, angle_deg, u, v, 0.0) for u, v in local_ground]
    local_ground_sheet = polygon_sheet(hfss, f"{tag}_partial_ground", ground_points)

    port_half_w = 3.0 * feed_w
    p0 = local_to_global(cx, cy, angle_deg, u_port, -port_half_w, 0.0)
    p1 = local_to_global(cx, cy, angle_deg, u_port, port_half_w, 0.0)
    p2 = local_to_global(cx, cy, angle_deg, u_port, port_half_w, h)
    p3 = local_to_global(cx, cy, angle_deg, u_port, -port_half_w, h)
    port_sheet = polygon_sheet(hfss, f"{tag}_wave_port_sheet", [p0, p1, p2, p3], None)
    hfss.wave_port(
        port_sheet.name,
        reference=local_ground_sheet.name,
        create_pec_cap=True,
        integration_line=hfss.axis_directions.ZPos,
        modes=1,
        impedance=50,
        name=f"P{tag[-1]}",
        renormalize=True,
        deembed=0,
        is_microstrip=True,
    )

    return [disc.name, feed.name, local_ground_sheet.name], port_sheet.name


def add_decoupling_vias(hfss: Hfss, params: dict) -> list[str]:
    """Add grounded via rings between elements to improve isolation."""
    h = params["substrate_h_mm"]
    names = []
    radius = params["ebg_ring_radius_mm"]
    pitch = params["ebg_pitch_mm"]
    via_r = params["ebg_via_radius_mm"]
    coords = []
    for x in [i * pitch for i in range(-3, 4)]:
        coords.append((x, radius))
        coords.append((x, -radius))
    for y in [i * pitch for i in range(-3, 4)]:
        coords.append((radius, y))
        coords.append((-radius, y))

    seen = set()
    for idx, (x, y) in enumerate(coords, start=1):
        key = (round(x, 4), round(y, 4))
        if key in seen:
            continue
        seen.add(key)
        via = hfss.modeler.create_cylinder(
            "Z",
            [x, y, 0],
            via_r,
            h,
            name=f"iso_via_{idx:02d}",
            material="copper",
        )
        names.append(via.name)
    return names


def add_isolation_walls(hfss: Hfss, params: dict) -> list[str]:
    """Add thin vertical PEC septa between adjacent elements."""
    h = params["substrate_h_mm"]
    start = params["iso_wall_start_mm"]
    stop = params["iso_wall_len_mm"]
    names = []
    for idx, angle in enumerate([45.0, 135.0, 225.0, 315.0], start=1):
        a = math.radians(angle)
        p_start = [start * math.cos(a), start * math.sin(a), 0.0]
        p_stop = [stop * math.cos(a), stop * math.sin(a), 0.0]
        wall_points = [
            p_start,
            p_stop,
            [p_stop[0], p_stop[1], h],
            [p_start[0], p_start[1], h],
        ]
        wall = polygon_sheet(hfss, f"iso_wall_{idx}", wall_points)
        names.append(wall.name)
    return names


def create_reports(hfss: Hfss, setup_name: str, sweep_name: str):
    solution = f"{setup_name} : {sweep_name}"
    try:
        s_terms = hfss.get_traces_for_plot(category="dB(S")
        hfss.post.create_report(
            expressions=s_terms,
            setup_sweep_name=solution,
            report_category="Modal Solution Data",
            plot_name="CH9_S_Parameters_and_Isolation",
        )
    except Exception as exc:  # Reports can be added after the first solve too.
        print(f"Report creation deferred: {exc}")


def build_project(
    analyze: bool = False,
    non_graphical: bool = False,
    quick: bool = False,
    sparam_only: bool = False,
) -> Path:
    print("Stage: starting AEDT/project build", flush=True)
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
        # Keep the old result next to the new one for traceability.
        backup = PROJECT_PATH.with_suffix(".previous.aedt")
        try:
            if backup.exists():
                backup.unlink()
            PROJECT_PATH.replace(backup)
        except OSError:
            pass

    hfss = Hfss(
        project=str(PROJECT_PATH),
        design="Array4_Diamond_CP_Patch",
        solution_type="DrivenModal",
        version="2023.1",
        non_graphical=non_graphical,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    hfss.modeler.model_units = "mm"

    substrate_material = add_ro4350b(hfss)
    print("Stage: materials ready", flush=True)

    board = PARAMS["board_side_mm"]
    half = board / 2.0
    h = PARAMS["substrate_h_mm"]
    d = PARAMS["element_spacing_mm"]
    r = d / math.sqrt(2.0)

    substrate = hfss.modeler.create_box(
        [-half, -half, 0],
        [board, board, h],
        name="RO4350B_substrate",
        material=substrate_material,
    )
    substrate.transparency = 0.65

    print("Stage: substrate created", flush=True)

    metal_names = []
    port_sheets = []
    for tag, angle in ELEMENTS:
        cx = r * math.cos(math.radians(angle))
        cy = r * math.sin(math.radians(angle))
        metals, port_sheet = add_cp_patch_element(hfss, tag, (cx, cy), angle, PARAMS)
        metal_names.extend(metals)
        port_sheets.append(port_sheet)
    if PARAMS.get("iso_vias_enabled", 0.0) >= 0.5:
        metal_names.extend(add_decoupling_vias(hfss, PARAMS))
    if PARAMS.get("iso_walls_enabled", 0.0) >= 0.5:
        metal_names.extend(add_isolation_walls(hfss, PARAMS))
    print("Stage: four CP elements and ports created", flush=True)

    hfss.assign_perfecte_to_sheets(metal_names, name="PEC_metallization", is_infinite_ground=False)
    print("Stage: metallization PEC boundaries created", flush=True)

    hfss.create_open_region(
        frequency=f"{PARAMS['air_frequency_ghz']}GHz",
        boundary="Radiation",
        apply_infinite_ground=False,
    )
    print("Stage: radiation open region created", flush=True)
    if not quick and not sparam_only:
        hfss.insert_infinite_sphere(
            theta_start=0,
            theta_stop=90,
            theta_step=5,
            phi_start=0,
            phi_stop=360,
            phi_step=5,
            name="Upper_Hemisphere_5deg",
        )
        print("Stage: upper hemisphere far-field setup created", flush=True)
    else:
        print("Stage: S-parameter tuning mode skips far-field sphere creation", flush=True)

    max_passes = 4 if quick else 5 if sparam_only else 7
    min_passes = 1 if quick else 1 if sparam_only else 2
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
        sweep = hfss.create_single_point_sweep(
            setup=setup.name,
            unit="GHz",
            freq=PARAMS["freq_center_ghz"],
            name="Sweep_CH9",
            save_single_field=True,
            save_fields=False,
            save_rad_fields=False,
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

    if not quick:
        create_reports(hfss, setup.name, sweep.name)
        print("Stage: report definitions created", flush=True)
    else:
        print("Stage: quick mode skips report definitions", flush=True)

    notes = {
        "project": str(PROJECT_PATH),
        "design": hfss.design_name,
        "model": "Four microstrip-fed UWB planar monopole elements in a diamond layout.",
        "element_centers_mm": {
            tag: [
                round(r * math.cos(math.radians(angle)), 6),
                round(r * math.sin(math.radians(angle)), 6),
            ]
            for tag, angle in ELEMENTS
        },
        "nearest_neighbor_spacing_mm": PARAMS["element_spacing_mm"],
        "ports": ["P1", "P2", "P3", "P4"],
        "limitations": [
            "Initial synthesis model. Final compliance requires completed HFSS solve and numerical optimization.",
            "PEC metallization is used for faster first-pass simulation.",
            "The current fast-tuning topology is optimized first for S-parameters and isolation; circular-polarization and far-field metrics must be verified on the full-field solve.",
        ],
        "parameters": PARAMS,
    }
    PARAM_PATH.write_text(json.dumps(notes, indent=2), encoding="utf-8")

    hfss.save_project()
    print("Stage: project saved", flush=True)

    if analyze:
        print("Stage: analysis started", flush=True)
        ok = hfss.analyze_setup(setup.name, cores=4, tasks=4, blocking=True)
        print(f"Analyze result: {ok}")
        hfss.save_project()
        print("Stage: solved project saved", flush=True)

    hfss.release_desktop(close_projects=False, close_desktop=non_graphical)
    return PROJECT_PATH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true", help="Run HFSS solve after building the model.")
    parser.add_argument("--non-graphical", action="store_true", help="Launch AEDT in non-graphical mode.")
    parser.add_argument("--quick", action="store_true", help="Use a single 8 GHz sweep point for fast tuning.")
    parser.add_argument("--sparam-only", action="store_true", help="Skip far fields and save only S-parameter sweep data.")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Override a numeric design parameter, for example --param patch_l_mm=12.0.",
    )
    args = parser.parse_args()
    for item in args.param:
        key, value = item.split("=", 1)
        PARAMS[key] = float(value)
    path = build_project(
        analyze=args.analyze,
        non_graphical=args.non_graphical,
        quick=args.quick,
        sparam_only=args.sparam_only,
    )
    print(path)


if __name__ == "__main__":
    main()

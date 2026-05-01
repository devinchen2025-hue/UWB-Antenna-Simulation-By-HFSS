from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44.aedt"
PARAM_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_params.json"
RESULTS_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44.aedtresults"
PYAEDT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44.pyaedt"


PARAMS = {
    "freq_center_ghz": 8.0,
    "freq_start_ghz": 7.5,
    "freq_stop_ghz": 8.5,
    "freq_step_ghz": 0.02,
    "target_start_ghz": 7.738,
    "target_stop_ghz": 8.233,
    "wide_start_ghz": 7.7,
    "wide_stop_ghz": 8.3,
    "element_spacing_mm": 17.0,
    "board_diameter_mm": 44.0,
    "flat_port_edges_enabled": 1.0,
    "substrate_h_mm": 0.508,
    "copper_t_mm": 0.035,
    "epsr": 3.48,
    "tan_delta": 0.0037,
    "disc_radius_mm": 3.8,
    "feed_w_mm": 2.3,
    "partial_ground_w_mm": 10.0,
    "partial_ground_gap_mm": 0.3,
    "edge_clearance_mm": 0.8,
    "port_width_factor": 2.0,
    "meander_enabled": 0.0,
    "meander_offset_mm": 4.0,
    "meander_u1_mm": 3.6,
    "meander_u2_mm": 6.2,
    "iso_vias_enabled": 0.0,
    "ebg_via_radius_mm": 0.16,
    "ebg_pitch_mm": 2.0,
    "ebg_ring_radius_mm": 7.2,
    "air_frequency_ghz": 7.0,
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


def rectangle_segment_points(
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


def clipped_circle_points(radius: float, cut: float, z: float, arc_steps: int = 18) -> list[list[float]]:
    """Return a CCW circular PCB outline clipped by four flat port edges."""
    yc = math.sqrt(max(radius * radius - cut * cut, 0.0))
    a = math.atan2(yc, cut)

    def arc(start: float, stop: float) -> list[tuple[float, float]]:
        return [
            (radius * math.cos(start + (stop - start) * i / arc_steps),
             radius * math.sin(start + (stop - start) * i / arc_steps))
            for i in range(1, arc_steps + 1)
        ]

    points: list[tuple[float, float]] = [(cut, -yc), (cut, yc)]
    points.extend(arc(a, math.pi / 2.0 - a))
    points.append((-yc, cut))
    points.extend(arc(math.pi / 2.0 + a, math.pi - a))
    points.append((-cut, -yc))
    points.extend(arc(math.pi + a, 1.5 * math.pi - a))
    points.append((yc, -cut))
    points.extend(arc(1.5 * math.pi + a, 2.0 * math.pi - a))

    cleaned: list[list[float]] = []
    seen_last: tuple[float, float] | None = None
    for x, y in points:
        key = (round(x, 6), round(y, 6))
        if key == seen_last:
            continue
        cleaned.append([x, y, z])
        seen_last = key
    return cleaned


def add_ro4350b(hfss: Hfss, params: dict) -> str:
    mat_name = "RO4350B_custom_D44"
    if mat_name not in hfss.materials.material_keys:
        mat = hfss.materials.add_material(mat_name)
        mat.permittivity = params["epsr"]
        mat.dielectric_loss_tangent = params["tan_delta"]
    return mat_name


def add_d44_element(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
) -> tuple[list[str], str]:
    """Create one microstrip-fed UWB element constrained inside a 44 mm circular PCB."""
    cx, cy = center
    h = params["substrate_h_mm"]
    feed_w = params["feed_w_mm"]
    radius = params["disc_radius_mm"]
    ground_w = params["partial_ground_w_mm"]
    ground_gap = params["partial_ground_gap_mm"]
    board_radius = params["board_diameter_mm"] / 2.0
    center_radius = params["element_spacing_mm"] / math.sqrt(2.0)
    u_port = board_radius - center_radius - params["edge_clearance_mm"]

    if u_port <= radius + ground_gap + 0.5:
        raise ValueError("44 mm PCB leaves too little radial feed length for the selected radiator size.")

    disc = hfss.modeler.create_circle(
        "XY",
        [cx, cy, h],
        radius,
        num_sides=72,
        name=f"{tag}_disc",
        material="copper",
    )

    feed_overlap_u = -0.35 * radius
    feed_names = []
    half_feed = feed_w / 2.0
    if params.get("meander_enabled", 0.0) >= 0.5:
        u1 = min(max(params["meander_u1_mm"], feed_overlap_u + feed_w), u_port - 2.5 * feed_w)
        u2 = min(max(params["meander_u2_mm"], u1 + 1.2 * feed_w), u_port - 1.2 * feed_w)
        offset = params["meander_offset_mm"]
        segments = [
            (feed_overlap_u, u1, -half_feed, half_feed),
            (u1 - half_feed, u1 + half_feed, 0.0, offset),
            (u1, u2, offset - half_feed, offset + half_feed),
            (u2 - half_feed, u2 + half_feed, 0.0, offset),
            (u2, u_port, -half_feed, half_feed),
        ]
        for idx, (u_min, u_max, v_min, v_max) in enumerate(segments, start=1):
            points = rectangle_segment_points(cx, cy, angle_deg, u_min, u_max, v_min, v_max, h)
            feed = polygon_sheet(hfss, f"{tag}_feed_meander_{idx}", points)
            feed_names.append(feed.name)
    else:
        feed_points = rectangle_segment_points(
            cx,
            cy,
            angle_deg,
            feed_overlap_u,
            u_port,
            -half_feed,
            half_feed,
            h,
        )
        feed = polygon_sheet(hfss, f"{tag}_feed_line", feed_points)
        feed_names.append(feed.name)

    u_ground_inner = radius + ground_gap
    local_ground = [
        (u_ground_inner, -ground_w / 2.0),
        (u_port, -ground_w / 2.0),
        (u_port, ground_w / 2.0),
        (u_ground_inner, ground_w / 2.0),
    ]
    ground_points = [local_to_global(cx, cy, angle_deg, u, v, 0.0) for u, v in local_ground]
    local_ground_sheet = polygon_sheet(hfss, f"{tag}_partial_ground", ground_points)

    port_half_w = params["port_width_factor"] * feed_w
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

    return [disc.name, *feed_names, local_ground_sheet.name], port_sheet.name


def add_decoupling_vias(hfss: Hfss, params: dict) -> list[str]:
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
            num_sides=16,
            name=f"iso_via_{idx:02d}",
            material="copper",
        )
        names.append(via.name)
    return names


def create_reports(hfss: Hfss, setup_name: str, sweep_name: str):
    solution = f"{setup_name} : {sweep_name}"
    try:
        hfss.post.create_report(
            expressions=hfss.get_traces_for_plot(category="dB(S"),
            setup_sweep_name=solution,
            report_category="Modal Solution Data",
            plot_name="D44_S_Parameters_and_Isolation",
        )
    except Exception as exc:
        print(f"Report creation deferred: {exc}")


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
    sparam_only: bool = False,
) -> Path:
    print("Stage: starting D44 AEDT/project build", flush=True)
    clean_previous_outputs()

    hfss = Hfss(
        project=str(PROJECT_PATH),
        design="Array4_Diamond_D44",
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

    if PARAMS.get("flat_port_edges_enabled", 0.0) >= 0.5:
        cut = board_radius - PARAMS["edge_clearance_mm"]
        substrate_sheet = polygon_sheet(
            hfss,
            "D44_RO4350B_clipped_circle_sheet",
            clipped_circle_points(board_radius, cut, 0.0),
            substrate_material,
        )
        substrate = hfss.modeler.thicken_sheet(substrate_sheet.name, h)
        substrate.name = "D44_RO4350B_clipped_circular_substrate"
        substrate.material_name = substrate_material
    else:
        substrate = hfss.modeler.create_cylinder(
            "Z",
            [0, 0, 0],
            board_radius,
            h,
            num_sides=128,
            name="D44_RO4350B_circular_substrate",
            material=substrate_material,
        )
    substrate.transparency = 0.65
    print("Stage: 44 mm circular substrate created", flush=True)

    metal_names = []
    for tag, angle in ELEMENTS:
        cx = center_radius * math.cos(math.radians(angle))
        cy = center_radius * math.sin(math.radians(angle))
        metals, _ = add_d44_element(hfss, tag, (cx, cy), angle, PARAMS)
        metal_names.extend(metals)
    if PARAMS.get("iso_vias_enabled", 0.0) >= 0.5:
        metal_names.extend(add_decoupling_vias(hfss, PARAMS))
    print("Stage: four D44 elements and ports created", flush=True)

    hfss.assign_perfecte_to_sheets(metal_names, name="D44_PEC_metallization", is_infinite_ground=False)
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

    notes = {
        "project": str(PROJECT_PATH),
        "design": hfss.design_name,
        "model": "D44 circular PCB variant with four microstrip-fed UWB planar monopole elements in a diamond layout.",
        "pcb_constraint": "Circular PCB, diameter 44 mm.",
        "element_centers_mm": {
            tag: [
                round(center_radius * math.cos(math.radians(angle)), 6),
                round(center_radius * math.sin(math.radians(angle)), 6),
            ]
            for tag, angle in ELEMENTS
        },
        "nearest_neighbor_spacing_mm": PARAMS["element_spacing_mm"],
        "ports": ["P1", "P2", "P3", "P4"],
        "limitations": [
            "D44 constrained optimization model. Final compliance requires completed HFSS solve and numerical optimization.",
            "PEC metallization is used for faster first-pass simulation.",
            "This topology is optimized first for S-parameters under the 44 mm circular PCB constraint; CP and far-field metrics require a dedicated CP radiator/feed network.",
        ],
        "parameters": PARAMS,
    }
    PARAM_PATH.write_text(json.dumps(notes, indent=2), encoding="utf-8")

    hfss.save_project()
    print("Stage: D44 project saved", flush=True)

    if analyze:
        print("Stage: D44 analysis started", flush=True)
        ok = hfss.analyze_setup(setup.name, cores=4, tasks=4, blocking=True)
        print(f"Analyze result: {ok}", flush=True)
        hfss.save_project()
        print("Stage: solved D44 project saved", flush=True)

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
        help="Override a numeric design parameter, for example --param disc_radius_mm=3.8.",
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

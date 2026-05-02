from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]

BASE_PARAMS = {
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
    "patch_side_mm": 9.0,
    "corner_cut_mm": 0.84,
    "feed_offset_u_mm": 2.74,
    "feed_offset_v_mm": 0.0,
    "feed_pad_radius_mm": 0.45,
    "port_width_mm": 0.75,
    "isolation_slot_enabled": 1.0,
    "isolation_slot_length_mm": 11.0,
    "isolation_slot_width_mm": 0.45,
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

TOPOLOGIES = {
    "dualfeed": {
        "label": "DUALFEED_CP",
        "design": "Array4_Diamond_D44_DualFeed_CP",
        "description": "Dual orthogonal feed square patches. Each element exposes A/B feeds intended for 90 degree CP excitation.",
        "kind": "dualfeed",
        "params": {
            "patch_side_mm": 9.15,
            "corner_cut_mm": 0.0,
            "feed_offset_u_mm": 2.45,
            "feed_pad_radius_mm": 0.42,
            "port_width_mm": 0.70,
            "isolation_slot_length_mm": 10.0,
            "isolation_slot_width_mm": 0.42,
        },
    },
    "hybrid": {
        "label": "HYBRID90_CP",
        "design": "Array4_Diamond_D44_Hybrid90_CP",
        "description": "Dual-feed patches with ideal 90 degree hybrid excitation intent and printable branch traces for network layout study.",
        "kind": "hybrid",
        "params": {
            "patch_side_mm": 9.15,
            "corner_cut_mm": 0.0,
            "feed_offset_u_mm": 2.45,
            "feed_pad_radius_mm": 0.42,
            "port_width_mm": 0.70,
            "hybrid_trace_width_mm": 0.32,
            "hybrid_trace_gap_mm": 0.55,
            "isolation_slot_length_mm": 10.0,
            "isolation_slot_width_mm": 0.42,
        },
    },
    "slotcoupled": {
        "label": "SLOTCOUPLED_CP",
        "design": "Array4_Diamond_D44_SlotCoupled_CP",
        "description": "Aperture-coupled top patches fed by underside microstrip lines through ground slots.",
        "kind": "slotcoupled",
        "params": {
            "patch_side_mm": 9.55,
            "corner_cut_mm": 0.72,
            "feed_offset_u_mm": 0.0,
            "aperture_length_mm": 4.2,
            "aperture_width_mm": 0.55,
            "feedline_length_mm": 9.0,
            "feedline_width_mm": 0.70,
            "feedline_z_mm": -0.18,
            "port_width_mm": 0.70,
            "isolation_slot_length_mm": 8.0,
            "isolation_slot_width_mm": 0.35,
        },
    },
    "stacked": {
        "label": "STACKED_PARASITIC_CP",
        "design": "Array4_Diamond_D44_StackedParasitic_CP",
        "description": "Driven corner-truncated patches plus stacked parasitic patches using the available 8 mm height margin.",
        "kind": "stacked",
        "params": {
            "patch_side_mm": 8.95,
            "corner_cut_mm": 0.84,
            "feed_offset_u_mm": 2.70,
            "parasitic_side_mm": 10.35,
            "parasitic_corner_cut_mm": 0.65,
            "air_gap_mm": 2.25,
            "isolation_slot_length_mm": 10.0,
            "isolation_slot_width_mm": 0.42,
        },
    },
}


def topology_paths(topology: str) -> dict[str, Path]:
    label = TOPOLOGIES[topology]["label"]
    project = ROOT / f"UWB_CH9_Diamond_CP_Array_D44_{label}.aedt"
    return {
        "project": project,
        "params": ROOT / f"UWB_CH9_Diamond_CP_Array_D44_{label}_params.json",
        "results": ROOT / f"UWB_CH9_Diamond_CP_Array_D44_{label}.aedtresults",
        "pyaedt": ROOT / f"UWB_CH9_Diamond_CP_Array_D44_{label}.pyaedt",
    }


def topology_params(topology: str) -> dict:
    params = dict(BASE_PARAMS)
    params.update(TOPOLOGIES[topology].get("params", {}))
    return params


def local_to_global(cx: float, cy: float, angle_deg: float, u: float, v: float, z: float) -> list[float]:
    angle = math.radians(angle_deg)
    eu = (math.cos(angle), math.sin(angle))
    ev = (-math.sin(angle), math.cos(angle))
    return [cx + u * eu[0] + v * ev[0], cy + u * eu[1] + v * ev[1], z]


def rectangle_points(cx: float, cy: float, angle_deg: float, u_min: float, u_max: float, v_min: float, v_max: float, z: float) -> list[list[float]]:
    return [
        local_to_global(cx, cy, angle_deg, u_min, v_min, z),
        local_to_global(cx, cy, angle_deg, u_max, v_min, z),
        local_to_global(cx, cy, angle_deg, u_max, v_max, z),
        local_to_global(cx, cy, angle_deg, u_min, v_max, z),
    ]


def polygon_sheet(hfss: Hfss, name: str, points: list[list[float]], material: str | None = "copper"):
    return hfss.modeler.create_polyline(points, cover_surface=True, close_surface=True, name=name, material=material)


def patch_points(cx: float, cy: float, angle_deg: float, side: float, cut: float, z: float) -> list[list[float]]:
    half = side / 2.0
    if cut <= 1e-9:
        local = [(-half, -half), (half, -half), (half, half), (-half, half)]
    else:
        local = [
            (-half + cut, -half),
            (half, -half),
            (half, half - cut),
            (half - cut, half),
            (-half, half),
            (-half, -half + cut),
        ]
    return [local_to_global(cx, cy, angle_deg, u, v, z) for u, v in local]


def add_ro4350b(hfss: Hfss, params: dict) -> str:
    mat_name = "RO4350B_custom_D44_Topology"
    if mat_name not in hfss.materials.material_keys:
        mat = hfss.materials.add_material(mat_name)
        mat.permittivity = params["epsr"]
        mat.dielectric_loss_tangent = params["tan_delta"]
    return mat_name


def add_lumped_feed(
    hfss: Hfss,
    name: str,
    center: tuple[float, float],
    angle_deg: float,
    feed_u: float,
    feed_v: float,
    top_z: float,
    bottom_z: float,
    params: dict,
    pad: bool = True,
) -> list[str]:
    cx, cy = center
    feed = local_to_global(cx, cy, angle_deg, feed_u, feed_v, top_z)
    base = local_to_global(cx, cy, angle_deg, feed_u, feed_v, bottom_z)
    metals = []
    if pad:
        pad_obj = hfss.modeler.create_circle(
            "XY",
            feed,
            params["feed_pad_radius_mm"],
            num_sides=36,
            name=f"{name}_feed_pad",
            material="copper",
        )
        metals.append(pad_obj.name)
    half_w = params["port_width_mm"] / 2.0
    p0 = local_to_global(cx, cy, angle_deg, feed_u, feed_v - half_w, bottom_z)
    p1 = local_to_global(cx, cy, angle_deg, feed_u, feed_v + half_w, bottom_z)
    p2 = local_to_global(cx, cy, angle_deg, feed_u, feed_v + half_w, top_z)
    p3 = local_to_global(cx, cy, angle_deg, feed_u, feed_v - half_w, top_z)
    port_sheet = polygon_sheet(hfss, f"{name}_lumped_port_sheet", [p0, p1, p2, p3], None)
    hfss.lumped_port(
        port_sheet.name,
        create_port_sheet=False,
        integration_line=[feed, base],
        impedance=50,
        name=name,
        renormalize=True,
    )
    return metals


def add_isolation_slot_sheets(hfss: Hfss, params: dict) -> list[str]:
    if params.get("isolation_slot_enabled", 0.0) < 0.5:
        return []
    names = []
    inner = params["isolation_slot_inner_mm"]
    length = params["isolation_slot_length_mm"]
    width = params["isolation_slot_width_mm"]
    for idx, angle in enumerate([45.0, 135.0, 225.0, 315.0], start=1):
        pts = rectangle_points(0.0, 0.0, angle, inner, inner + length, -width / 2.0, width / 2.0, 0.0)
        names.append(polygon_sheet(hfss, f"ground_isolation_slot_{idx}", pts, "vacuum").name)
    return names


def add_dualfeed_element(hfss: Hfss, tag: str, center: tuple[float, float], angle: float, params: dict, hybrid_traces: bool = False) -> list[str]:
    metals = []
    h = params["substrate_h_mm"]
    patch = polygon_sheet(
        hfss,
        f"{tag}_dualfeed_square_patch",
        patch_points(*center, angle, params["patch_side_mm"], 0.0, h),
    )
    metals.append(patch.name)
    f = params["feed_offset_u_mm"]
    metals += add_lumped_feed(hfss, f"P{tag[-1]}A", center, angle, f, 0.0, h, 0.0, params)
    metals += add_lumped_feed(hfss, f"P{tag[-1]}B", center, angle, 0.0, f, h, 0.0, params)
    if hybrid_traces:
        w = params.get("hybrid_trace_width_mm", 0.32)
        gap = params.get("hybrid_trace_gap_mm", 0.55)
        # Printable trace placeholders for later layout; sources remain the two hybrid output nodes.
        for suffix, u0, u1, v0, v1 in [
            ("trace_a", -f - gap, f, -w / 2, w / 2),
            ("trace_b", -w / 2, w / 2, -f - gap, f),
            ("quarter_stub_a", -f - gap, -f, w, w + 1.6),
            ("quarter_stub_b", -w - 1.6, -w, -f - gap, -f),
        ]:
            trace = polygon_sheet(hfss, f"{tag}_hybrid_{suffix}", rectangle_points(*center, angle, u0, u1, v0, v1, h), "copper")
            metals.append(trace.name)
    return metals


def add_singlefeed_element(hfss: Hfss, tag: str, center: tuple[float, float], angle: float, params: dict, stacked: bool = False) -> list[str]:
    metals = []
    h = params["substrate_h_mm"]
    driven = polygon_sheet(
        hfss,
        f"{tag}_driven_cp_patch",
        patch_points(*center, angle, params["patch_side_mm"], params["corner_cut_mm"], h),
    )
    metals.append(driven.name)
    metals += add_lumped_feed(hfss, f"P{tag[-1]}", center, angle, params["feed_offset_u_mm"], params["feed_offset_v_mm"], h, 0.0, params)
    if stacked:
        z = h + params["air_gap_mm"]
        parasitic = polygon_sheet(
            hfss,
            f"{tag}_stacked_parasitic_patch",
            patch_points(*center, angle, params["parasitic_side_mm"], params["parasitic_corner_cut_mm"], z),
        )
        metals.append(parasitic.name)
    return metals


def add_slotcoupled_element(hfss: Hfss, tag: str, center: tuple[float, float], angle: float, params: dict) -> tuple[list[str], list[str]]:
    metals = []
    slots = []
    h = params["substrate_h_mm"]
    patch = polygon_sheet(
        hfss,
        f"{tag}_slotcoupled_patch",
        patch_points(*center, angle, params["patch_side_mm"], params["corner_cut_mm"], h),
    )
    metals.append(patch.name)
    aperture = polygon_sheet(
        hfss,
        f"{tag}_aperture_slot",
        rectangle_points(*center, angle, -params["aperture_length_mm"] / 2.0, params["aperture_length_mm"] / 2.0, -params["aperture_width_mm"] / 2.0, params["aperture_width_mm"] / 2.0, 0.0),
        "vacuum",
    )
    slots.append(aperture.name)
    z = params["feedline_z_mm"]
    half_l = params["feedline_length_mm"] / 2.0
    half_w = params["feedline_width_mm"] / 2.0
    line = polygon_sheet(hfss, f"{tag}_underside_feedline", rectangle_points(*center, angle, -half_l, half_l, -half_w, half_w, z), "copper")
    metals.append(line.name)
    # The port is at one line end and references the ground plane above.
    metals += add_lumped_feed(hfss, f"P{tag[-1]}", center, angle, -half_l, 0.0, 0.0, z, params, pad=False)
    return metals, slots


def validate_params(params: dict) -> None:
    top_height = params["substrate_h_mm"] + 2.0 * params["copper_t_mm"] + params.get("air_gap_mm", 0.0)
    if params.get("parasitic_side_mm"):
        top_height += params["copper_t_mm"]
    if top_height > params["total_height_limit_mm"]:
        raise ValueError(f"Total height {top_height:.3f} mm exceeds {params['total_height_limit_mm']:.3f} mm")
    if params["ground_radius_mm"] > params["board_diameter_mm"] / 2.0:
        raise ValueError("Ground radius must stay inside board")
    board_radius = params["board_diameter_mm"] / 2.0
    center_radius = params["element_spacing_mm"] / math.sqrt(2.0)
    max_side = max(params["patch_side_mm"], params.get("parasitic_side_mm", params["patch_side_mm"]))
    if center_radius + max_side / math.sqrt(2.0) > board_radius - 0.25:
        raise ValueError("Patch corner too close to board edge")


def clean_outputs(paths: dict[str, Path]) -> None:
    for path in [paths["results"], paths["pyaedt"], paths["project"].with_suffix(".aedt.lock")]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    path.unlink()
                except OSError:
                    pass
    if paths["project"].exists():
        backup = paths["project"].with_suffix(".previous.aedt")
        try:
            if backup.exists():
                backup.unlink()
            paths["project"].replace(backup)
        except OSError:
            pass


def create_reports(hfss: Hfss, setup_name: str, sweep_name: str, plot_prefix: str) -> None:
    solution = f"{setup_name} : {sweep_name}"
    try:
        hfss.post.create_report(
            expressions=hfss.get_traces_for_plot(category="dB(S"),
            setup_sweep_name=solution,
            report_category="Modal Solution Data",
            plot_name=f"{plot_prefix}_S_Parameters",
        )
    except Exception as exc:
        print(f"S-parameter report creation deferred: {exc}", flush=True)
    for expression, name in [
        ("dB(GainTotal)", f"{plot_prefix}_GainTotal_8GHz"),
        ("AxialRatioValue", f"{plot_prefix}_AxialRatio_8GHz"),
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


def build_project(topology: str, analyze: bool = False, non_graphical: bool = False, quick: bool = False, band_samples: bool = False, sparam_only: bool = False) -> Path:
    spec = TOPOLOGIES[topology]
    params = topology_params(topology)
    validate_params(params)
    paths = topology_paths(topology)
    clean_outputs(paths)
    print(f"Stage: starting {spec['label']} AEDT/project build", flush=True)

    hfss = Hfss(
        project=str(paths["project"]),
        design=spec["design"],
        solution_type="DrivenModal",
        version="2023.1",
        non_graphical=non_graphical,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    hfss.modeler.model_units = "mm"

    substrate_material = add_ro4350b(hfss, params)
    board_radius = params["board_diameter_mm"] / 2.0
    h = params["substrate_h_mm"]
    center_radius = params["element_spacing_mm"] / math.sqrt(2.0)
    substrate = hfss.modeler.create_cylinder("Z", [0, 0, 0], board_radius, h, num_sides=128, name=f"{spec['label']}_substrate", material=substrate_material)
    substrate.transparency = 0.65
    ground = hfss.modeler.create_circle("XY", [0, 0, 0], params["ground_radius_mm"], num_sides=128, name=f"{spec['label']}_bottom_ground", material="copper")
    metal_names = [ground.name]
    slot_names = add_isolation_slot_sheets(hfss, params)
    print("Stage: substrate, ground, and isolation slots created", flush=True)

    kind = spec["kind"]
    for tag, angle in ELEMENTS:
        cx = center_radius * math.cos(math.radians(angle))
        cy = center_radius * math.sin(math.radians(angle))
        if kind == "dualfeed":
            metal_names.extend(add_dualfeed_element(hfss, tag, (cx, cy), angle, params))
        elif kind == "hybrid":
            metal_names.extend(add_dualfeed_element(hfss, tag, (cx, cy), angle, params, hybrid_traces=True))
        elif kind == "slotcoupled":
            metals, slots = add_slotcoupled_element(hfss, tag, (cx, cy), angle, params)
            metal_names.extend(metals)
            slot_names.extend(slots)
        elif kind == "stacked":
            metal_names.extend(add_singlefeed_element(hfss, tag, (cx, cy), angle, params, stacked=True))
        else:
            raise ValueError(f"Unsupported topology kind {kind}")
    print(f"Stage: {spec['label']} radiators and feeds created", flush=True)

    if slot_names:
        try:
            hfss.modeler.subtract(ground.name, slot_names, keep_originals=False)
            print("Stage: ground slots cut", flush=True)
        except Exception as exc:
            print(f"Ground slot subtraction deferred/failed: {exc}", flush=True)

    hfss.assign_perfecte_to_sheets(metal_names, name=f"{spec['label']}_PEC_metallization", is_infinite_ground=False)
    hfss.create_open_region(frequency=f"{params['air_frequency_ghz']}GHz", boundary="Radiation", apply_infinite_ground=False)
    if not sparam_only:
        hfss.insert_infinite_sphere(theta_start=0, theta_stop=90, theta_step=5, phi_start=0, phi_stop=360, phi_step=5, name="Upper_Hemisphere_5deg")
        print("Stage: radiation region and upper-hemisphere sphere created", flush=True)
    else:
        print("Stage: S-parameter-only mode skips far-field sphere creation", flush=True)

    max_passes = 4 if quick else 5 if sparam_only else 7
    min_passes = 1 if quick or sparam_only else 2
    max_delta_s = 0.05 if quick else 0.03 if sparam_only else 0.02
    setup = hfss.create_setup(
        name="Setup_CH9",
        setup_type="HFSSDriven",
        Frequency=f"{params['freq_center_ghz']}GHz",
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
                start_frequency=params["target_start_ghz"],
                stop_frequency=params["target_stop_ghz"],
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
                freq=params["freq_center_ghz"],
                name="Sweep_CH9",
                save_single_field=not sparam_only,
                save_fields=not sparam_only,
                save_rad_fields=not sparam_only,
            )
    else:
        sweep = hfss.create_linear_step_sweep(
            setup=setup.name,
            unit="GHz",
            start_frequency=params["freq_start_ghz"],
            stop_frequency=params["freq_stop_ghz"],
            step_size=params["freq_step_ghz"],
            name="Sweep_CH9",
            save_fields=not sparam_only,
            save_rad_fields=not sparam_only,
            sweep_type="Discrete",
        )
    if not sparam_only:
        create_reports(hfss, setup.name, sweep.name, spec["label"])
    print("Stage: setup, sweep, and reports created", flush=True)

    total_height = params["substrate_h_mm"] + 2.0 * params["copper_t_mm"] + params.get("air_gap_mm", 0.0)
    if params.get("parasitic_side_mm"):
        total_height += params["copper_t_mm"]
    notes = {
        "project": str(paths["project"]),
        "design": hfss.design_name,
        "topology": topology,
        "label": spec["label"],
        "model": spec["description"],
        "pcb_constraint": "Circular PCB, diameter 44 mm.",
        "height_constraint": f"PCB + copper/topology height {total_height:.3f} mm <= {params['total_height_limit_mm']} mm.",
        "cp_target": "AxialRatioValue <= 3 dB in the selected FOV and CH9 frequencies.",
        "fov_target": "Theta 0-360 deg, Phi 45-90 deg, GainTotal min >= -5 dBi.",
        "source_guidance": source_guidance(topology),
        "parameters": params,
    }
    paths["params"].write_text(json.dumps(notes, indent=2), encoding="utf-8")

    hfss.save_project()
    if analyze:
        print(f"Stage: {spec['label']} analysis started", flush=True)
        ok = hfss.analyze_setup(setup.name, cores=4, tasks=4, blocking=True)
        print(f"Analyze result: {ok}", flush=True)
        hfss.save_project()
    hfss.release_desktop(close_projects=False, close_desktop=non_graphical)
    return paths["project"]


def source_guidance(topology: str) -> list[str]:
    if topology in {"dualfeed", "hybrid"}:
        return [
            "A/B feeds on each patch are intended for 90 degree quadrature excitation.",
            "Use per-element quadrature source cases for CP checks.",
            "The hybrid topology includes printable branch trace placeholders; final layout needs a controlled-impedance network extraction.",
        ]
    if topology == "slotcoupled":
        return [
            "Ports feed underside microstrip lines through aperture slots in the ground plane.",
            "Tune aperture length/width and feedline offset before final signoff.",
        ]
    if topology == "stacked":
        return [
            "Driven patches are single-feed corner-truncated patches.",
            "Stacked parasitic patches use available height to broaden impedance/AR behavior.",
        ]
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", choices=sorted(TOPOLOGIES), required=True)
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--non-graphical", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--band-samples", action="store_true")
    parser.add_argument("--sparam-only", action="store_true")
    parser.add_argument("--param", action="append", default=[], help="Override topology parameter, e.g. --param patch_side_mm=9.2")
    args = parser.parse_args()
    if args.param:
        spec_params = TOPOLOGIES[args.topology].setdefault("params", {})
        for item in args.param:
            key, value = item.split("=", 1)
            spec_params[key] = float(value)
    path = build_project(
        args.topology,
        analyze=args.analyze,
        non_graphical=args.non_graphical,
        quick=args.quick,
        band_samples=args.band_samples,
        sparam_only=args.sparam_only,
    )
    print(path)


if __name__ == "__main__":
    main()

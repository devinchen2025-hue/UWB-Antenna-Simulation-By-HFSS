from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ansys.aedt.core import Hfss
from ansys.aedt.core.application.design_solutions import DesignSolution
from ansys.aedt.core.application.variables import VariableManager
from ansys.aedt.core.generic.constants import SolutionsHfss
from ansys.aedt.core.modeler.cad.primitives import GeometryModeler
from ansys.aedt.core.modules.material_lib import Material, Materials, _arg2dict, settings


ROOT = Path(__file__).resolve().parents[1]
AEDT_EXE = Path(r"D:\Program Files\AnsysEM\v231\Win64\ansysedt.exe")
PYAEDT_SOLVE_HELPER = ROOT / "scripts" / "solve_uwb_ch9_d44_existing_setup.py"


def patch_pyaedt_empty_variable_lists() -> None:
    if getattr(VariableManager, "_d44_none_variable_guard", False):
        variables_patched = True
    else:
        variables_patched = False

    if not variables_patched:
        def _get_var_list_from_aedt(self, desktop_object):
            var_list = []
            if self._app._is_object_oriented_enabled() and self._app.design_type not in [
                "Maxwell Circuit",
                "Circuit Netlist",
            ]:
                if self._app.design_type in [
                    "Circuit Design",
                    "Twin Builder",
                    "HFSS 3D Layout Design",
                ] and "GetDesignName" in dir(desktop_object):
                    try:
                        v = list(self._app.get_oo_object(desktop_object, "DefinitionParameters").GetPropNames() or [])
                    except AttributeError:
                        v = []
                    var_list = v

                try:
                    v = list(self._app.get_oo_object(desktop_object, "Variables").GetPropNames() or [])
                except AttributeError:
                    v = []
                var_list += v
                if self._app._aedt_version >= "2025.2":
                    return var_list

            if "GetVariables" in desktop_object.__dir__():
                raw_variables = desktop_object.GetVariables()
                if raw_variables:
                    var_list += [i for i in list(raw_variables) if i not in var_list]
            try:
                raw_array_variables = desktop_object.GetArrayVariables()
                if raw_array_variables:
                    var_list += [i for i in list(raw_array_variables) if i not in var_list]
            except Exception:
                self._app.logger.debug("Could not retrieve array variables.")
            return var_list

        VariableManager._get_var_list_from_aedt = _get_var_list_from_aedt
        VariableManager._d44_none_variable_guard = True

    if getattr(Materials, "_d44_none_material_guard", False):
        return

    def _aedmattolibrary(self, matname):
        project_materials = self.odefinition_manager.GetProjectMaterialNames() or []
        if matname not in project_materials and not (settings.remote_api or settings.remote_rpc_session):
            matname = self._get_aedt_case_name(matname)
        props = {}
        _arg2dict(list(self.omaterial_manager.GetData(matname) or []), props)
        values_view = props.values()
        value_iterator = iter(values_view)
        first_value = next(value_iterator)
        newmat = Material(self, matname, first_value, material_update=False)
        newmat._material_update = True
        self.material_keys[matname.casefold()] = newmat
        return self.material_keys[matname.casefold()]

    Materials._aedmattolibrary = _aedmattolibrary
    Materials._d44_none_material_guard = True

    if getattr(GeometryModeler, "_d44_fast_material_guard", False):
        return

    original_check_material = GeometryModeler._check_material

    def _check_material(self, material, default_material, threshold=100000):
        material_name = material.name if isinstance(material, Material) else str(material or default_material)
        key = material_name.casefold()
        if key in {"copper", "pec"}:
            return material_name, False
        if key in {"vacuum", "air"} or key.startswith("ro4350b_custom"):
            return material_name, True
        return original_check_material(self, material, default_material, threshold)

    GeometryModeler._check_material = _check_material
    GeometryModeler._d44_fast_material_guard = True

    if getattr(DesignSolution, "_d44_solution_type_guard", False):
        return

    original_solution_type = DesignSolution.solution_type.fget
    original_solution_type_setter = DesignSolution.solution_type.fset

    def _solution_type(self):
        try:
            value = original_solution_type(self)
        except (AttributeError, TypeError):
            value = None
        if value in (None, "DrivenModal"):
            value = SolutionsHfss.DrivenModal
            self._solution_type = value
        return value

    DesignSolution.solution_type = property(_solution_type, original_solution_type_setter)
    DesignSolution._d44_solution_type_guard = True

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
    "microstrip_feed_enabled": 0.0,
    "microstrip_feed_offset_mm": 0.0,
    "microstrip_feedline_length_mm": 2.0,
    "microstrip_feedline_width_mm": 0.60,
    "microstrip_match_length_mm": 0.85,
    "microstrip_match_width_mm": 0.42,
    "microstrip_transform2_length_mm": 0.0,
    "microstrip_transform2_width_mm": 0.50,
    "microstrip_stub_length_mm": 0.0,
    "microstrip_stub_width_mm": 0.24,
    "microstrip_stub_offset_mm": 0.75,
    "microstrip_feed_mirror_enabled": 0.0,
    "neutralization_branch_enabled": 0.0,
    "neutralization_branch_length_mm": 1.15,
    "neutralization_branch_width_mm": 0.18,
    "neutralization_branch_offset_mm": 1.15,
    "weak_coupling_open_line_enabled": 0.0,
    "weak_coupling_open_line_length_mm": 2.20,
    "weak_coupling_open_line_width_mm": 0.12,
    "weak_coupling_open_line_offset_mm": 1.65,
    "weak_coupling_open_line_gap_mm": 0.08,
    "via_fence_enabled": 0.0,
    "via_fence_count": 3.0,
    "via_fence_radius_mm": 0.10,
    "via_fence_pitch_mm": 0.55,
    "via_fence_edge_offset_mm": 0.45,
    "via_fence_center_mm": 3.30,
    "local_dgs_enabled": 0.0,
    "local_dgs_length_mm": 4.8,
    "local_dgs_width_mm": 0.28,
    "local_dgs_offset_mm": 1.15,
    "hybrid_output_match_length_mm": 0.95,
    "hybrid_output_match_width_mm": 0.40,
    "dualpol_parasitic_enabled": 0.0,
    "parasitic_side_mm": 0.0,
    "parasitic_corner_cut_mm": 0.0,
    "parasitic_rotation_deg": 0.0,
    "parasitic_offset_u_mm": 0.0,
    "parasitic_offset_v_mm": 0.0,
    "air_gap_mm": 0.0,
    "dualpol_slotcoupled_enabled": 0.0,
    "feed_substrate_h_mm": 0.254,
    "slot_coupled_aperture_length_a_mm": 3.6,
    "slot_coupled_aperture_length_b_mm": 3.6,
    "slot_coupled_aperture_width_mm": 0.45,
    "slot_coupled_offset_a_mm": 0.0,
    "slot_coupled_offset_b_mm": 0.0,
    "slot_coupled_aperture_center_a_v_mm": 0.0,
    "slot_coupled_aperture_center_b_u_mm": 0.0,
    "slot_coupled_feedline_length_mm": 10.0,
    "slot_coupled_feedline_width_mm": 0.60,
    "slot_coupled_feedline_offset_a_v_mm": 0.0,
    "slot_coupled_feedline_offset_b_u_mm": 0.0,
    "slot_coupled_b_feed_layer_offset_mm": 0.0,
    "slot_coupled_bridge_enabled": 0.0,
    "slot_coupled_bridge_gap_mm": 1.10,
    "slot_coupled_bridge_offset_mm": 0.0,
    "slot_coupled_bridge_width_mm": 0.60,
    "slot_coupled_bridge_resonator_width_mm": 0.0,
    "slot_coupled_bridge_overhang_mm": 0.0,
    "slot_coupled_a_resonator_length_mm": 0.0,
    "slot_coupled_a_resonator_width_mm": 0.0,
    "slot_coupled_shield_via_enabled": 0.0,
    "slot_coupled_shield_via_count": 1.0,
    "slot_coupled_shield_via_radius_mm": 0.06,
    "slot_coupled_shield_via_offset_mm": 0.68,
    "slot_coupled_shield_via_pitch_mm": 0.42,
    "slot_coupled_shield_via_grounded": 1.0,
    "slot_coupled_shield_via_top_gap_mm": 0.03,
    "slot_coupled_a_neck_enabled": 0.0,
    "slot_coupled_a_neck_length_mm": 2.2,
    "slot_coupled_a_neck_width_mm": 0.30,
    "slot_coupled_underfeed_neutralizer_enabled": 0.0,
    "slot_coupled_underfeed_neutralizer_length_mm": 2.2,
    "slot_coupled_underfeed_neutralizer_width_mm": 0.12,
    "slot_coupled_underfeed_neutralizer_offset_mm": 1.20,
    "slot_coupled_underfeed_neutralizer_z_offset_mm": 0.06,
    "slot_coupled_patch_slit_enabled": 0.0,
    "slot_coupled_patch_slit_length_mm": 3.0,
    "slot_coupled_patch_slit_width_mm": 0.10,
    "slot_coupled_patch_slit_angle_deg": 45.0,
    "slot_coupled_patch_slit_offset_u_mm": 0.0,
    "slot_coupled_patch_slit_offset_v_mm": 0.0,
    "slot_coupled_horizon_loop_enabled": 0.0,
    "slot_coupled_horizon_loop_inner_side_mm": 6.2,
    "slot_coupled_horizon_loop_offset_u_mm": 0.0,
    "slot_coupled_horizon_loop_offset_v_mm": 0.0,
    "slot_coupled_edge_arm_enabled": 0.0,
    "slot_coupled_edge_arm_length_mm": 2.4,
    "slot_coupled_edge_arm_width_mm": 0.30,
    "slot_coupled_edge_arm_offset_mm": 0.0,
    "slot_coupled_edge_arm_gap_mm": 0.0,
    "slot_coupled_edge_wall_enabled": 0.0,
    "slot_coupled_edge_wall_height_mm": 2.0,
    "slot_coupled_edge_wall_width_mm": 0.50,
    "slot_coupled_edge_wall_offset_mm": 0.0,
    "slot_coupled_board_edge_ifa_enabled": 0.0,
    "slot_coupled_board_edge_ifa_length_mm": 4.6,
    "slot_coupled_board_edge_ifa_width_mm": 0.35,
    "slot_coupled_board_edge_ifa_height_mm": 3.8,
    "slot_coupled_board_edge_ifa_gap_mm": 0.15,
    "slot_coupled_board_edge_ifa_offset_mm": 0.0,
    "slot_coupled_folded_edge_arm_enabled": 0.0,
    "slot_coupled_folded_edge_arm_radial_length_mm": 1.8,
    "slot_coupled_folded_edge_arm_tangent_length_mm": 5.5,
    "slot_coupled_folded_edge_arm_width_mm": 0.30,
    "slot_coupled_folded_edge_arm_height_mm": 5.2,
    "slot_coupled_folded_edge_arm_offset_mm": 0.0,
    "slot_coupled_folded_edge_arm_gap_mm": 0.0,
    "slot_coupled_folded_edge_arm_turn_sign": 1.0,
    "board_edge_fed_monopole_enabled": 0.0,
    "board_edge_fed_monopole_height_mm": 4.8,
    "board_edge_fed_monopole_width_mm": 0.24,
    "board_edge_fed_monopole_gap_mm": 0.80,
    "board_edge_fed_monopole_offset_mm": 0.0,
    "board_edge_fed_monopole_topload_length_mm": 0.0,
    "board_edge_fed_ifa_enabled": 0.0,
    "board_edge_fed_ifa_length_mm": 3.8,
    "board_edge_fed_ifa_height_mm": 5.2,
    "board_edge_fed_ifa_width_mm": 0.24,
    "board_edge_fed_ifa_gap_mm": 0.60,
    "board_edge_fed_ifa_feed_offset_mm": 0.70,
    "board_edge_fed_ifa_offset_mm": 0.0,
    "board_edge_fed_l_match_enabled": 0.0,
    "board_edge_fed_l_match_stub_length_mm": 0.0,
    "board_edge_fed_l_match_stub_width_mm": 0.18,
    "board_edge_fed_l_match_stub_side_sign": 1.0,
    "board_edge_fed_l_match_fold_enabled": 0.0,
    "board_edge_fed_l_match_fold_length_mm": 0.0,
    "board_edge_fed_l_match_fold_width_mm": 0.14,
    "board_edge_fed_l_match_fold_radial_sign": 1.0,
    "board_edge_fed_l_match_capacitance_pf": 0.0,
    "board_edge_fed_l_match_inductance_nh": 0.0,
    "board_edge_fed_l_match_resistance_ohm": 0.0,
    "board_edge_fed_l_series_match_enabled": 0.0,
    "board_edge_fed_l_series_match_width_mm": 0.14,
    "board_edge_fed_l_series_match_capacitance_pf": 0.0,
    "board_edge_fed_l_series_match_inductance_nh": 0.0,
    "board_edge_fed_l_series_match_resistance_ohm": 0.0,
    "board_edge_fed_l_feed_neck_enabled": 0.0,
    "board_edge_fed_l_feed_neck_length_mm": 0.0,
    "board_edge_fed_l_feed_neck_width_mm": 0.14,
    "board_edge_fed_l_feed_neck_side_sign": 1.0,
    "slot_coupled_ab_cancel_enabled": 0.0,
    "slot_coupled_ab_cancel_coupling_length_mm": 1.60,
    "slot_coupled_ab_cancel_trace_width_mm": 0.12,
    "slot_coupled_ab_cancel_gap_mm": 0.08,
    "slot_coupled_ab_cancel_phase_offset_mm": 2.00,
    "slot_coupled_ab_cancel_side_sign": 1.0,
    "slot_coupled_ab_cancel_z_offset_mm": 0.0,
    "rf_switch_equiv_enabled": 0.0,
    "rf_switch_active_pol": 0.0,
    "rf_switch_off_resistance_ohm": 50.0,
    "rf_switch_off_capacitance_pf": 0.08,
    "rf_switch_off_inductance_nh": 0.0,
    "slot_coupled_stub_enabled": 0.0,
    "slot_coupled_stub_length_mm": 0.0,
    "slot_coupled_stub_width_mm": 0.25,
    "slot_coupled_stub_offset_mm": 2.0,
    "slot_coupled_stub_side_sign": 1.0,
    "slot_coupled_stub2_enabled": 0.0,
    "slot_coupled_stub2_length_mm": 0.0,
    "slot_coupled_stub2_width_mm": 0.25,
    "slot_coupled_stub2_offset_mm": 3.0,
    "slot_coupled_stub2_side_sign": -1.0,
    "slot_coupled_step_enabled": 0.0,
    "slot_coupled_step_length_mm": 0.0,
    "slot_coupled_step_width_mm": 0.80,
    "isolation_slot_enabled": 1.0,
    "isolation_slot_length_mm": 11.0,
    "isolation_slot_width_mm": 0.45,
    "isolation_slot_inner_mm": 3.2,
    "analysis_cores": 8.0,
    "analysis_tasks": 8.0,
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
            "patch_side_mm": 9.25,
            "corner_cut_mm": 0.0,
            "feed_offset_u_mm": 2.45,
            "feed_pad_radius_mm": 0.42,
            "port_width_mm": 0.70,
            "microstrip_feed_enabled": 0.0,
            "microstrip_feed_offset_mm": 0.0,
            "microstrip_feedline_length_mm": 2.0,
            "microstrip_feedline_width_mm": 0.60,
            "microstrip_match_length_mm": 0.85,
            "microstrip_match_width_mm": 0.42,
            "microstrip_stub_length_mm": 0.0,
            "microstrip_stub_width_mm": 0.24,
            "microstrip_stub_offset_mm": 0.75,
            "neutralization_branch_enabled": 0.0,
            "neutralization_branch_length_mm": 1.15,
            "neutralization_branch_width_mm": 0.18,
            "neutralization_branch_offset_mm": 1.15,
            "local_dgs_enabled": 0.0,
            "local_dgs_length_mm": 4.8,
            "local_dgs_width_mm": 0.28,
            "local_dgs_offset_mm": 1.15,
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
            "microstrip_feed_enabled": 0.0,
            "microstrip_feed_offset_mm": 0.0,
            "microstrip_feedline_length_mm": 2.0,
            "microstrip_feedline_width_mm": 0.60,
            "microstrip_match_length_mm": 0.85,
            "microstrip_match_width_mm": 0.42,
            "microstrip_stub_length_mm": 0.0,
            "microstrip_stub_width_mm": 0.24,
            "microstrip_stub_offset_mm": 0.75,
            "neutralization_branch_enabled": 0.0,
            "neutralization_branch_length_mm": 1.15,
            "neutralization_branch_width_mm": 0.18,
            "neutralization_branch_offset_mm": 1.15,
            "local_dgs_enabled": 0.0,
            "local_dgs_length_mm": 4.8,
            "local_dgs_width_mm": 0.28,
            "local_dgs_offset_mm": 1.15,
            "hybrid_output_match_length_mm": 0.95,
            "hybrid_output_match_width_mm": 0.40,
            "isolation_slot_length_mm": 10.0,
            "isolation_slot_width_mm": 0.42,
        },
    },
    "dualpol": {
        "label": "DUALPOL_XY",
        "design": "Array4_Diamond_D44_DualPolarized_XY",
        "description": "Dual-polarized square patches with independent global X/Y ports for polarization-diverse PDOA reception.",
        "kind": "dualpol",
        "params": {
            "patch_side_mm": 9.15,
            "corner_cut_mm": 0.0,
            "feed_offset_u_mm": 3.40,
            "feed_offset_v_mm": 0.0,
            "feed_pad_radius_mm": 0.28,
            "port_width_mm": 0.50,
            "microstrip_feed_enabled": 1.0,
            "microstrip_feed_offset_mm": 0.0,
            "microstrip_feedline_length_mm": 1.78,
            "microstrip_feedline_width_mm": 0.58,
            "microstrip_match_length_mm": 0.48,
            "microstrip_match_width_mm": 0.34,
            "microstrip_transform2_length_mm": 0.55,
            "microstrip_transform2_width_mm": 0.50,
            "microstrip_stub_length_mm": 0.0,
            "microstrip_stub_width_mm": 0.24,
            "microstrip_stub_offset_mm": 0.60,
            "microstrip_feed_mirror_enabled": 1.0,
            "neutralization_branch_enabled": 0.0,
            "neutralization_branch_length_mm": 0.85,
            "neutralization_branch_width_mm": 0.12,
            "neutralization_branch_offset_mm": 0.65,
            "local_dgs_enabled": 0.0,
            "local_dgs_length_mm": 3.6,
            "local_dgs_width_mm": 0.18,
            "local_dgs_offset_mm": 0.75,
            "dualpol_parasitic_enabled": 1.0,
            "parasitic_side_mm": 9.75,
            "parasitic_corner_cut_mm": 0.0,
            "parasitic_rotation_deg": 0.0,
            "parasitic_offset_u_mm": 0.0,
            "parasitic_offset_v_mm": 0.0,
            "air_gap_mm": 1.20,
            "dualpol_slotcoupled_enabled": 0.0,
            "feed_substrate_h_mm": 0.254,
            "slot_coupled_aperture_length_a_mm": 3.6,
            "slot_coupled_aperture_length_b_mm": 3.6,
            "slot_coupled_aperture_width_mm": 0.45,
            "slot_coupled_offset_a_mm": 0.0,
            "slot_coupled_offset_b_mm": 0.0,
            "slot_coupled_aperture_center_a_v_mm": 0.0,
            "slot_coupled_aperture_center_b_u_mm": 0.0,
            "slot_coupled_feedline_length_mm": 10.0,
            "slot_coupled_feedline_width_mm": 0.60,
            "slot_coupled_feedline_offset_a_v_mm": 0.0,
            "slot_coupled_feedline_offset_b_u_mm": 0.0,
            "slot_coupled_b_feed_layer_offset_mm": 0.0,
            "slot_coupled_bridge_enabled": 0.0,
            "slot_coupled_bridge_gap_mm": 1.10,
            "slot_coupled_bridge_offset_mm": 0.0,
            "slot_coupled_bridge_width_mm": 0.60,
            "slot_coupled_bridge_resonator_width_mm": 0.0,
            "slot_coupled_bridge_overhang_mm": 0.0,
            "slot_coupled_a_resonator_length_mm": 0.0,
            "slot_coupled_a_resonator_width_mm": 0.0,
            "slot_coupled_shield_via_enabled": 0.0,
            "slot_coupled_shield_via_count": 1.0,
            "slot_coupled_shield_via_radius_mm": 0.06,
            "slot_coupled_shield_via_offset_mm": 0.68,
            "slot_coupled_shield_via_pitch_mm": 0.42,
            "slot_coupled_shield_via_grounded": 1.0,
            "slot_coupled_shield_via_top_gap_mm": 0.03,
            "slot_coupled_a_neck_enabled": 0.0,
            "slot_coupled_a_neck_length_mm": 2.2,
            "slot_coupled_a_neck_width_mm": 0.30,
            "slot_coupled_underfeed_neutralizer_enabled": 0.0,
            "slot_coupled_underfeed_neutralizer_length_mm": 2.2,
            "slot_coupled_underfeed_neutralizer_width_mm": 0.12,
            "slot_coupled_underfeed_neutralizer_offset_mm": 1.20,
            "slot_coupled_underfeed_neutralizer_z_offset_mm": 0.06,
            "slot_coupled_patch_slit_enabled": 0.0,
            "slot_coupled_patch_slit_length_mm": 3.0,
            "slot_coupled_patch_slit_width_mm": 0.10,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.0,
            "slot_coupled_patch_slit_offset_v_mm": 0.0,
            "slot_coupled_ab_cancel_enabled": 0.0,
            "slot_coupled_ab_cancel_coupling_length_mm": 1.60,
            "slot_coupled_ab_cancel_trace_width_mm": 0.12,
            "slot_coupled_ab_cancel_gap_mm": 0.08,
            "slot_coupled_ab_cancel_phase_offset_mm": 2.00,
            "slot_coupled_ab_cancel_side_sign": 1.0,
            "slot_coupled_ab_cancel_z_offset_mm": 0.0,
            "rf_switch_equiv_enabled": 0.0,
            "rf_switch_active_pol": 0.0,
            "rf_switch_off_resistance_ohm": 50.0,
            "rf_switch_off_capacitance_pf": 0.08,
            "rf_switch_off_inductance_nh": 0.0,
            "slot_coupled_stub_enabled": 0.0,
            "slot_coupled_stub_length_mm": 0.0,
            "slot_coupled_stub_width_mm": 0.25,
            "slot_coupled_stub_offset_mm": 2.0,
            "slot_coupled_stub_side_sign": 1.0,
            "slot_coupled_stub2_enabled": 0.0,
            "slot_coupled_stub2_length_mm": 0.0,
            "slot_coupled_stub2_width_mm": 0.25,
            "slot_coupled_stub2_offset_mm": 3.0,
            "slot_coupled_stub2_side_sign": -1.0,
            "slot_coupled_step_enabled": 0.0,
            "slot_coupled_step_length_mm": 0.0,
            "slot_coupled_step_width_mm": 0.80,
            "weak_coupling_open_line_enabled": 0.0,
            "via_fence_enabled": 0.0,
            "isolation_slot_enabled": 1.0,
            "isolation_slot_length_mm": 10.0,
            "isolation_slot_width_mm": 0.42,
            "isolation_slot_inner_mm": 3.20,
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


def has_stacked_parasitic(params: dict) -> bool:
    side = params.get("parasitic_side_mm", 0.0)
    if side <= 0.0:
        return False
    if "dualpol_parasitic_enabled" in params:
        return params.get("dualpol_parasitic_enabled", 0.0) >= 0.5
    return True


def has_dualpol_slotcoupled(params: dict) -> bool:
    return params.get("dualpol_slotcoupled_enabled", 0.0) >= 0.5


def single_source_feed_name(params: dict) -> str:
    if params.get("single_source_feed_enabled", 0.0) < 0.5:
        return ""
    return str(params.get("single_source_feed_name", "")).strip()


def source_feed_selected(params: dict, name: str) -> bool:
    selected = single_source_feed_name(params)
    return not selected or selected == name


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
    port_width_axis: str = "v",
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
    if port_width_axis == "u":
        p0 = local_to_global(cx, cy, angle_deg, feed_u - half_w, feed_v, bottom_z)
        p1 = local_to_global(cx, cy, angle_deg, feed_u + half_w, feed_v, bottom_z)
        p2 = local_to_global(cx, cy, angle_deg, feed_u + half_w, feed_v, top_z)
        p3 = local_to_global(cx, cy, angle_deg, feed_u - half_w, feed_v, top_z)
    else:
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


def add_lumped_switch_load(
    hfss: Hfss,
    name: str,
    center: tuple[float, float],
    angle_deg: float,
    feed_u: float,
    feed_v: float,
    top_z: float,
    bottom_z: float,
    params: dict,
    port_width_axis: str = "v",
) -> None:
    cx, cy = center
    feed = local_to_global(cx, cy, angle_deg, feed_u, feed_v, top_z)
    base = local_to_global(cx, cy, angle_deg, feed_u, feed_v, bottom_z)
    half_w = params["port_width_mm"] / 2.0
    if port_width_axis == "u":
        p0 = local_to_global(cx, cy, angle_deg, feed_u - half_w, feed_v, bottom_z)
        p1 = local_to_global(cx, cy, angle_deg, feed_u + half_w, feed_v, bottom_z)
        p2 = local_to_global(cx, cy, angle_deg, feed_u + half_w, feed_v, top_z)
        p3 = local_to_global(cx, cy, angle_deg, feed_u - half_w, feed_v, top_z)
    else:
        p0 = local_to_global(cx, cy, angle_deg, feed_u, feed_v - half_w, bottom_z)
        p1 = local_to_global(cx, cy, angle_deg, feed_u, feed_v + half_w, bottom_z)
        p2 = local_to_global(cx, cy, angle_deg, feed_u, feed_v + half_w, top_z)
        p3 = local_to_global(cx, cy, angle_deg, feed_u, feed_v - half_w, top_z)
    load_sheet = polygon_sheet(hfss, f"{name}_switch_off_load_sheet", [p0, p1, p2, p3], None)
    resistance = params.get("rf_switch_off_resistance_ohm", 50.0)
    capacitance = params.get("rf_switch_off_capacitance_pf", 0.08) * 1e-12
    inductance = params.get("rf_switch_off_inductance_nh", 0.0) * 1e-9
    hfss.assign_lumped_rlc_to_sheet(
        load_sheet.name,
        start_direction=[feed, base],
        name=f"{name}_switch_off_load",
        rlc_type="Parallel",
        resistance=resistance if resistance > 0.0 else None,
        capacitance=capacitance if capacitance > 0.0 else None,
        inductance=inductance if inductance > 0.0 else None,
    )


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


def add_local_dgs_slots(hfss: Hfss, params: dict) -> list[str]:
    if params.get("local_dgs_enabled", 0.0) < 0.5:
        return []
    names = []
    center_radius = params["element_spacing_mm"] / math.sqrt(2.0)
    length = params["local_dgs_length_mm"]
    width = params["local_dgs_width_mm"]
    offset = params["local_dgs_offset_mm"]
    for tag, angle in ELEMENTS:
        cx = center_radius * math.cos(math.radians(angle))
        cy = center_radius * math.sin(math.radians(angle))
        slot_a = rectangle_points(cx, cy, angle, offset - width / 2.0, offset + width / 2.0, -length / 2.0, length / 2.0, 0.0)
        slot_b = rectangle_points(cx, cy, angle, -length / 2.0, length / 2.0, offset - width / 2.0, offset + width / 2.0, 0.0)
        names.append(polygon_sheet(hfss, f"{tag}_local_dgs_u_slot", slot_a, "vacuum").name)
        names.append(polygon_sheet(hfss, f"{tag}_local_dgs_v_slot", slot_b, "vacuum").name)
    return names


def add_microstrip_edge_feed(
    hfss: Hfss,
    name: str,
    center: tuple[float, float],
    angle_deg: float,
    axis: str,
    params: dict,
    hybrid_outputs: bool = False,
    side_sign: float = 1.0,
) -> list[str]:
    h = params["substrate_h_mm"]
    side = params["patch_side_mm"]
    edge = side / 2.0
    side_sign = 1.0 if side_sign >= 0.0 else -1.0
    line_len = params["microstrip_feedline_length_mm"]
    line_w = params["microstrip_feedline_width_mm"]
    match_len_key = "hybrid_output_match_length_mm" if hybrid_outputs else "microstrip_match_length_mm"
    match_width_key = "hybrid_output_match_width_mm" if hybrid_outputs else "microstrip_match_width_mm"
    match_len = min(params.get(match_len_key, params["microstrip_match_length_mm"]), max(0.15, line_len - 0.1))
    match_w = params.get(match_width_key, params["microstrip_match_width_mm"])
    transform_len = max(0.0, params.get("microstrip_transform2_length_mm", 0.0))
    transform_len = min(transform_len, max(0.0, line_len - match_len - 0.1))
    transform_w = params.get("microstrip_transform2_width_mm", line_w)
    stub_len = params.get("microstrip_stub_length_mm", 0.0)
    stub_w = params.get("microstrip_stub_width_mm", 0.24)
    stub_offset = min(params.get("microstrip_stub_offset_mm", 0.75), max(0.15, line_len - 0.1))
    feed_shift = params.get("microstrip_feed_offset_mm", 0.0)
    overlap = 0.08
    metals = []

    def signed_span(start: float, stop: float) -> tuple[float, float]:
        a = side_sign * start
        b = side_sign * stop
        return min(a, b), max(a, b)

    def add_rect(suffix: str, u0: float, u1: float, v0: float, v1: float) -> None:
        sheet = polygon_sheet(hfss, f"{name}_{suffix}", rectangle_points(*center, angle_deg, u0, u1, v0, v1, h), "copper")
        metals.append(sheet.name)

    if axis == "u":
        u0, u1 = signed_span(edge - overlap, edge + match_len)
        add_rect("edge_match_section", u0, u1, feed_shift - match_w / 2.0, feed_shift + match_w / 2.0)
        feed_start = edge + match_len
        if transform_len > 1e-9:
            u0, u1 = signed_span(edge + match_len - overlap, edge + match_len + transform_len)
            add_rect("edge_transform_section", u0, u1, feed_shift - transform_w / 2.0, feed_shift + transform_w / 2.0)
            feed_start = edge + match_len + transform_len
        u0, u1 = signed_span(feed_start - overlap, edge + line_len)
        add_rect("edge_feedline", u0, u1, feed_shift - line_w / 2.0, feed_shift + line_w / 2.0)
        if stub_len > 1e-9:
            stub_u = side_sign * (edge + stub_offset)
            add_rect("open_stub", stub_u - stub_w / 2.0, stub_u + stub_w / 2.0, feed_shift + line_w / 2.0 - overlap, feed_shift + line_w / 2.0 + stub_len)
        metals += add_lumped_feed(hfss, name, center, angle_deg, side_sign * (edge + line_len), feed_shift, h, 0.0, params, pad=False)
    elif axis == "v":
        v0, v1 = signed_span(edge - overlap, edge + match_len)
        add_rect("edge_match_section", feed_shift - match_w / 2.0, feed_shift + match_w / 2.0, v0, v1)
        feed_start = edge + match_len
        if transform_len > 1e-9:
            v0, v1 = signed_span(edge + match_len - overlap, edge + match_len + transform_len)
            add_rect("edge_transform_section", feed_shift - transform_w / 2.0, feed_shift + transform_w / 2.0, v0, v1)
            feed_start = edge + match_len + transform_len
        v0, v1 = signed_span(feed_start - overlap, edge + line_len)
        add_rect("edge_feedline", feed_shift - line_w / 2.0, feed_shift + line_w / 2.0, v0, v1)
        if stub_len > 1e-9:
            stub_v = side_sign * (edge + stub_offset)
            add_rect("open_stub", feed_shift + line_w / 2.0 - overlap, feed_shift + line_w / 2.0 + stub_len, stub_v - stub_w / 2.0, stub_v + stub_w / 2.0)
        metals += add_lumped_feed(hfss, name, center, angle_deg, feed_shift, side_sign * (edge + line_len), h, 0.0, params, pad=False)
    else:
        raise ValueError(f"Unsupported feed axis {axis}")
    return metals


def add_neutralization_branch(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
    u_side_sign: float = 1.0,
    v_side_sign: float = 1.0,
) -> list[str]:
    if params.get("neutralization_branch_enabled", 0.0) < 0.5:
        return []
    h = params["substrate_h_mm"]
    edge = params["patch_side_mm"] / 2.0
    line_len = params["microstrip_feedline_length_mm"]
    line_w = params["microstrip_feedline_width_mm"]
    width = params["neutralization_branch_width_mm"]
    offset = min(params["neutralization_branch_offset_mm"], max(0.2, line_len - 0.15))
    length = min(params.get("neutralization_branch_length_mm", offset), max(0.2, line_len - 0.15))
    u_side_sign = 1.0 if u_side_sign >= 0.0 else -1.0
    v_side_sign = 1.0 if v_side_sign >= 0.0 else -1.0
    anchor_u = u_side_sign * (edge + offset)
    anchor_v = v_side_sign * (edge + offset)
    corner_u = u_side_sign * (edge + length)
    corner_v = v_side_sign * (edge + length)
    metals = []
    u_leg_u0, u_leg_u1 = sorted([anchor_u - width / 2.0, anchor_u + width / 2.0])
    u_leg_v0, u_leg_v1 = sorted([-v_side_sign * line_w / 2.0, corner_v + v_side_sign * width / 2.0])
    v_leg_u0, v_leg_u1 = sorted([-u_side_sign * line_w / 2.0, corner_u + u_side_sign * width / 2.0])
    v_leg_v0, v_leg_v1 = sorted([anchor_v - width / 2.0, anchor_v + width / 2.0])
    for suffix, u0, u1, v0, v1 in [
        ("neutralization_u_leg", u_leg_u0, u_leg_u1, u_leg_v0, u_leg_v1),
        ("neutralization_v_leg", v_leg_u0, v_leg_u1, v_leg_v0, v_leg_v1),
    ]:
        sheet = polygon_sheet(hfss, f"{tag}_{suffix}", rectangle_points(*center, angle_deg, u0, u1, v0, v1, h), "copper")
        metals.append(sheet.name)
    return metals


def mirrored_feed_side_sign(center: tuple[float, float], axis: str, params: dict) -> float:
    if params.get("microstrip_feed_mirror_enabled", 0.0) < 0.5:
        return 1.0
    coord = center[0] if axis == "u" else center[1]
    return -1.0 if coord < -1e-9 else 1.0


def rotated_rectangle_points(
    cx: float,
    cy: float,
    element_angle_deg: float,
    center_u: float,
    center_v: float,
    rect_angle_deg: float,
    length: float,
    width: float,
    z: float,
) -> list[list[float]]:
    rect_angle = math.radians(rect_angle_deg)
    ca = math.cos(rect_angle)
    sa = math.sin(rect_angle)
    pts = []
    for du, dv in [
        (-length / 2.0, -width / 2.0),
        (length / 2.0, -width / 2.0),
        (length / 2.0, width / 2.0),
        (-length / 2.0, width / 2.0),
    ]:
        u = center_u + du * ca - dv * sa
        v = center_v + du * sa + dv * ca
        pts.append(local_to_global(cx, cy, element_angle_deg, u, v, z))
    return pts


def add_weak_coupling_open_line(hfss: Hfss, tag: str, center: tuple[float, float], angle_deg: float, params: dict) -> list[str]:
    if params.get("weak_coupling_open_line_enabled", 0.0) < 0.5:
        return []
    h = params["substrate_h_mm"]
    length = params["weak_coupling_open_line_length_mm"]
    width = params["weak_coupling_open_line_width_mm"]
    offset = params.get("weak_coupling_open_line_offset_mm", params["feed_offset_u_mm"] / 2.0)
    gap = max(params.get("weak_coupling_open_line_gap_mm", 0.08), 0.02)
    pts = rotated_rectangle_points(
        *center,
        angle_deg,
        offset,
        offset,
        -45.0,
        length,
        width,
        h + gap,
    )
    line = polygon_sheet(hfss, f"{tag}_ab_weak_coupling_open_line", pts, "copper")
    return [line.name]


def add_via_fence(hfss: Hfss, tag: str, center: tuple[float, float], angle_deg: float, params: dict) -> None:
    if params.get("via_fence_enabled", 0.0) < 0.5:
        return
    h = params["substrate_h_mm"]
    edge = params["patch_side_mm"] / 2.0
    count = max(1, int(round(params.get("via_fence_count", 3.0))))
    radius = params.get("via_fence_radius_mm", 0.10)
    pitch = params.get("via_fence_pitch_mm", 0.55)
    edge_offset = params.get("via_fence_edge_offset_mm", 0.45)
    center_pos = params.get("via_fence_center_mm", params["feed_offset_u_mm"])
    max_pos = edge - radius - 0.20
    local_positions = []
    for idx in range(count):
        pos = center_pos + (idx - (count - 1) / 2.0) * pitch
        if 0.40 <= pos <= max_pos:
            local_positions.append(pos)
    if not local_positions:
        local_positions = [min(max(center_pos, 0.40), max_pos)]
    fence_u = edge + edge_offset
    for idx, pos in enumerate(local_positions, start=1):
        for suffix, u, v in [
            ("u_edge", fence_u, pos),
            ("v_edge", pos, fence_u),
        ]:
            origin = local_to_global(*center, angle_deg, u, v, 0.0)
            hfss.modeler.create_cylinder(
                "Z",
                origin,
                radius,
                h,
                num_sides=16,
                name=f"{tag}_ab_via_fence_{suffix}_{idx}",
                material="copper",
            )


def add_slotcoupled_shield_vias(hfss: Hfss, tag: str, center: tuple[float, float], angle_deg: float, params: dict) -> None:
    if params.get("slot_coupled_shield_via_enabled", 0.0) < 0.5:
        return
    feed_z_a = -params.get("feed_substrate_h_mm", 0.254)
    feed_z_b = feed_z_a - params.get("slot_coupled_b_feed_layer_offset_mm", 0.0)
    bridge_z = feed_z_b
    if params.get("slot_coupled_bridge_enabled", 0.0) >= 0.5:
        bridge_z -= params.get("slot_coupled_bridge_offset_mm", 0.0)
    bottom_z = min(feed_z_a, feed_z_b, bridge_z)
    if params.get("slot_coupled_shield_via_grounded", 1.0) >= 0.5:
        top_z = 0.0
    else:
        top_z = -max(params.get("slot_coupled_shield_via_top_gap_mm", 0.03), 0.01)
    height = top_z - bottom_z
    if height <= 1e-9:
        return
    count = max(1, int(round(params.get("slot_coupled_shield_via_count", 1.0))))
    radius = params.get("slot_coupled_shield_via_radius_mm", 0.06)
    offset = params.get("slot_coupled_shield_via_offset_mm", 0.68)
    pitch = params.get("slot_coupled_shield_via_pitch_mm", 0.42)
    for ring in range(count):
        d = offset + ring * pitch
        for idx, (u, v) in enumerate(((d, d), (-d, d), (-d, -d), (d, -d)), start=1):
            origin = local_to_global(*center, angle_deg, u, v, bottom_z)
            hfss.modeler.create_cylinder(
                "Z",
                origin,
                radius,
                height,
                num_sides=12,
                name=f"{tag}_slotcoupled_ab_shield_via_{ring + 1}_{idx}",
                material="copper",
            )


def add_slotcoupled_patch_slit(hfss: Hfss, tag: str, patch_name: str, center: tuple[float, float], angle_deg: float, params: dict) -> None:
    if params.get("slot_coupled_patch_slit_enabled", 0.0) < 0.5:
        return
    h = params["substrate_h_mm"]
    slit = polygon_sheet(
        hfss,
        f"{tag}_slotcoupled_patch_decoupling_slit",
        rotated_rectangle_points(
            *center,
            angle_deg,
            params.get("slot_coupled_patch_slit_offset_u_mm", 0.0),
            params.get("slot_coupled_patch_slit_offset_v_mm", 0.0),
            params.get("slot_coupled_patch_slit_angle_deg", 45.0),
            params.get("slot_coupled_patch_slit_length_mm", 3.0),
            params.get("slot_coupled_patch_slit_width_mm", 0.10),
            h,
        ),
        "vacuum",
    )
    hfss.modeler.subtract(patch_name, [slit.name], keep_originals=False)


def add_slotcoupled_horizon_loop(hfss: Hfss, tag: str, patch_name: str, center: tuple[float, float], angle_deg: float, params: dict) -> None:
    if params.get("slot_coupled_horizon_loop_enabled", 0.0) < 0.5:
        return
    h = params["substrate_h_mm"]
    inner_side = params.get("slot_coupled_horizon_loop_inner_side_mm", 0.0)
    offset_u = params.get("slot_coupled_horizon_loop_offset_u_mm", 0.0)
    offset_v = params.get("slot_coupled_horizon_loop_offset_v_mm", 0.0)
    hole = polygon_sheet(
        hfss,
        f"{tag}_slotcoupled_horizon_loop_hole",
        rectangle_points(
            *center,
            angle_deg,
            offset_u - inner_side / 2.0,
            offset_u + inner_side / 2.0,
            offset_v - inner_side / 2.0,
            offset_v + inner_side / 2.0,
            h,
        ),
        "vacuum",
    )
    hfss.modeler.subtract(patch_name, [hole.name], keep_originals=False)


def radial_edge_axis(center: tuple[float, float]) -> tuple[str, float]:
    cx, cy = center
    if abs(cx) >= abs(cy):
        return "u", 1.0 if cx >= 0.0 else -1.0
    return "v", 1.0 if cy >= 0.0 else -1.0


def add_slotcoupled_edge_radiators(hfss: Hfss, tag: str, center: tuple[float, float], angle_deg: float, params: dict) -> list[str]:
    metals: list[str] = []
    h = params["substrate_h_mm"]
    edge = params["patch_side_mm"] / 2.0
    axis, side = radial_edge_axis(center)

    if params.get("slot_coupled_edge_arm_enabled", 0.0) >= 0.5:
        length = params.get("slot_coupled_edge_arm_length_mm", 2.4)
        width = params.get("slot_coupled_edge_arm_width_mm", 0.30)
        offset = params.get("slot_coupled_edge_arm_offset_mm", 0.0)
        gap = params.get("slot_coupled_edge_arm_gap_mm", 0.0)
        overlap = 0.06 if gap <= 1e-9 else 0.0
        start = side * (edge + gap - overlap)
        stop = side * (edge + gap + length)
        span0, span1 = sorted([start, stop])
        cross0, cross1 = offset - width / 2.0, offset + width / 2.0
        if axis == "u":
            pts = rectangle_points(*center, angle_deg, span0, span1, cross0, cross1, h)
        else:
            pts = rectangle_points(*center, angle_deg, cross0, cross1, span0, span1, h)
        arm = polygon_sheet(hfss, f"{tag}_slotcoupled_radial_edge_arm", pts, "copper")
        metals.append(arm.name)

    if params.get("slot_coupled_edge_wall_enabled", 0.0) >= 0.5:
        height = params.get("slot_coupled_edge_wall_height_mm", 2.0)
        width = params.get("slot_coupled_edge_wall_width_mm", 0.50)
        offset = params.get("slot_coupled_edge_wall_offset_mm", 0.0)
        side_pos = side * edge
        cross0, cross1 = offset - width / 2.0, offset + width / 2.0
        if axis == "u":
            pts = [
                local_to_global(*center, angle_deg, side_pos, cross0, h),
                local_to_global(*center, angle_deg, side_pos, cross1, h),
                local_to_global(*center, angle_deg, side_pos, cross1, h + height),
                local_to_global(*center, angle_deg, side_pos, cross0, h + height),
            ]
        else:
            pts = [
                local_to_global(*center, angle_deg, cross0, side_pos, h),
                local_to_global(*center, angle_deg, cross1, side_pos, h),
                local_to_global(*center, angle_deg, cross1, side_pos, h + height),
                local_to_global(*center, angle_deg, cross0, side_pos, h + height),
            ]
        wall = polygon_sheet(hfss, f"{tag}_slotcoupled_radial_edge_wall", pts, "copper")
        metals.append(wall.name)

    if params.get("slot_coupled_board_edge_ifa_enabled", 0.0) >= 0.5:
        length = params.get("slot_coupled_board_edge_ifa_length_mm", 4.6)
        width = params.get("slot_coupled_board_edge_ifa_width_mm", 0.35)
        height = params.get("slot_coupled_board_edge_ifa_height_mm", 3.8)
        gap = params.get("slot_coupled_board_edge_ifa_gap_mm", 0.15)
        offset = params.get("slot_coupled_board_edge_ifa_offset_mm", 0.0)
        top_z = h + height
        start = side * (edge + gap)
        stop = side * (edge + gap + length)
        span0, span1 = sorted([start, stop])
        cross0, cross1 = offset - width / 2.0, offset + width / 2.0
        if axis == "u":
            top_pts = rectangle_points(*center, angle_deg, span0, span1, cross0, cross1, top_z)
            short_pts = [
                local_to_global(*center, angle_deg, start, cross0, 0.0),
                local_to_global(*center, angle_deg, start, cross1, 0.0),
                local_to_global(*center, angle_deg, start, cross1, top_z),
                local_to_global(*center, angle_deg, start, cross0, top_z),
            ]
        else:
            top_pts = rectangle_points(*center, angle_deg, cross0, cross1, span0, span1, top_z)
            short_pts = [
                local_to_global(*center, angle_deg, cross0, start, 0.0),
                local_to_global(*center, angle_deg, cross1, start, 0.0),
                local_to_global(*center, angle_deg, cross1, start, top_z),
                local_to_global(*center, angle_deg, cross0, start, top_z),
            ]
        top_arm = polygon_sheet(hfss, f"{tag}_slotcoupled_board_edge_ifa_top_arm", top_pts, "copper")
        short_wall = polygon_sheet(hfss, f"{tag}_slotcoupled_board_edge_ifa_short_wall", short_pts, "copper")
        metals.extend([top_arm.name, short_wall.name])

    if params.get("slot_coupled_folded_edge_arm_enabled", 0.0) >= 0.5:
        radial_len = params.get("slot_coupled_folded_edge_arm_radial_length_mm", 1.8)
        tangent_len = params.get("slot_coupled_folded_edge_arm_tangent_length_mm", 5.5)
        width = params.get("slot_coupled_folded_edge_arm_width_mm", 0.30)
        height = params.get("slot_coupled_folded_edge_arm_height_mm", 5.2)
        offset = params.get("slot_coupled_folded_edge_arm_offset_mm", 0.0)
        gap = params.get("slot_coupled_folded_edge_arm_gap_mm", 0.0)
        turn_sign = 1.0 if params.get("slot_coupled_folded_edge_arm_turn_sign", 1.0) >= 0.0 else -1.0
        top_z = h + height
        overlap = 0.06 if gap <= 1e-9 else 0.0
        start = side * (edge + gap - overlap)
        elbow = side * (edge + gap + radial_len)
        radial0, radial1 = sorted([start, elbow])
        cross0, cross1 = offset - width / 2.0, offset + width / 2.0
        tangent0 = offset
        tangent1 = offset + turn_sign * tangent_len
        tan0, tan1 = sorted([tangent0, tangent1])
        elbow0, elbow1 = sorted([elbow - side * width / 2.0, elbow + side * width / 2.0])
        if axis == "u":
            riser_pts = [
                local_to_global(*center, angle_deg, start, cross0, h),
                local_to_global(*center, angle_deg, start, cross1, h),
                local_to_global(*center, angle_deg, start, cross1, top_z),
                local_to_global(*center, angle_deg, start, cross0, top_z),
            ]
            radial_pts = rectangle_points(*center, angle_deg, radial0, radial1, cross0, cross1, top_z)
            tangent_pts = rectangle_points(*center, angle_deg, elbow0, elbow1, tan0, tan1, top_z)
        else:
            riser_pts = [
                local_to_global(*center, angle_deg, cross0, start, h),
                local_to_global(*center, angle_deg, cross1, start, h),
                local_to_global(*center, angle_deg, cross1, start, top_z),
                local_to_global(*center, angle_deg, cross0, start, top_z),
            ]
            radial_pts = rectangle_points(*center, angle_deg, cross0, cross1, radial0, radial1, top_z)
            tangent_pts = rectangle_points(*center, angle_deg, tan0, tan1, elbow0, elbow1, top_z)
        riser = polygon_sheet(hfss, f"{tag}_slotcoupled_folded_edge_riser", riser_pts, "copper")
        radial_arm = polygon_sheet(hfss, f"{tag}_slotcoupled_folded_edge_radial_arm", radial_pts, "copper")
        tangent_arm = polygon_sheet(hfss, f"{tag}_slotcoupled_folded_edge_tangent_arm", tangent_pts, "copper")
        metals.extend([riser.name, radial_arm.name, tangent_arm.name])

    return metals


def add_board_edge_fed_low_elevation_unit(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
) -> list[str]:
    metals: list[str] = []
    monopole_enabled = params.get("board_edge_fed_monopole_enabled", 0.0) >= 0.5
    ifa_enabled = params.get("board_edge_fed_ifa_enabled", 0.0) >= 0.5
    if not monopole_enabled and not ifa_enabled:
        return metals

    h = params["substrate_h_mm"]
    edge = params["patch_side_mm"] / 2.0
    axis, side = radial_edge_axis(center)
    port_name = f"P{tag[-1]}L"

    def add_match(feed_radial: float, feed_offset: float, feed_top_z: float) -> None:
        if params.get("board_edge_fed_l_match_enabled", 0.0) < 0.5:
            return
        stub_l = params.get("board_edge_fed_l_match_stub_length_mm", 0.0)
        stub_w = params.get("board_edge_fed_l_match_stub_width_mm", 0.18)
        stub_sign = 1.0 if params.get("board_edge_fed_l_match_stub_side_sign", 1.0) >= 0.0 else -1.0
        fold_enabled = params.get("board_edge_fed_l_match_fold_enabled", 0.0) >= 0.5
        fold_l = params.get("board_edge_fed_l_match_fold_length_mm", 0.0)
        fold_w = params.get("board_edge_fed_l_match_fold_width_mm", stub_w)
        fold_sign = 1.0 if params.get("board_edge_fed_l_match_fold_radial_sign", 1.0) >= 0.0 else -1.0
        cap_pf = params.get("board_edge_fed_l_match_capacitance_pf", 0.0)
        ind_nh = params.get("board_edge_fed_l_match_inductance_nh", 0.0)
        res_ohm = params.get("board_edge_fed_l_match_resistance_ohm", 0.0)
        match_offset = feed_offset
        match_radial = feed_radial
        if stub_l > 1e-9:
            match_offset = feed_offset + stub_sign * stub_l
            cross0, cross1 = sorted([feed_offset, match_offset])
            radial0, radial1 = sorted([side * feed_radial - stub_w / 2.0, side * feed_radial + stub_w / 2.0])
            if axis == "u":
                pts = rectangle_points(*center, angle_deg, radial0, radial1, cross0, cross1, feed_top_z)
            else:
                pts = rectangle_points(*center, angle_deg, cross0, cross1, radial0, radial1, feed_top_z)
            stub = polygon_sheet(hfss, f"{tag}_board_edge_fed_l_match_stub", pts, "copper")
            metals.append(stub.name)
        if fold_enabled and fold_l > 1e-9:
            match_radial = feed_radial + fold_sign * fold_l
            cross0, cross1 = sorted([match_offset - fold_w / 2.0, match_offset + fold_w / 2.0])
            radial0, radial1 = sorted([side * (feed_radial - fold_w / 2.0), side * match_radial])
            if axis == "u":
                pts = rectangle_points(*center, angle_deg, radial0, radial1, cross0, cross1, feed_top_z)
            else:
                pts = rectangle_points(*center, angle_deg, cross0, cross1, radial0, radial1, feed_top_z)
            fold = polygon_sheet(hfss, f"{tag}_board_edge_fed_l_match_fold", pts, "copper")
            metals.append(fold.name)
        if cap_pf <= 0.0 and ind_nh <= 0.0 and res_ohm <= 0.0:
            return
        match_params = dict(params)
        match_params["rf_switch_off_resistance_ohm"] = res_ohm
        match_params["rf_switch_off_capacitance_pf"] = cap_pf
        match_params["rf_switch_off_inductance_nh"] = ind_nh
        if axis == "u":
            add_lumped_switch_load(
                hfss,
                f"{port_name}_shunt_match",
                center,
                angle_deg,
                side * match_radial,
                match_offset,
                feed_top_z,
                0.0,
                match_params,
            )
        else:
            add_lumped_switch_load(
                hfss,
                f"{port_name}_shunt_match",
                center,
                angle_deg,
                match_offset,
                side * match_radial,
                feed_top_z,
                0.0,
                match_params,
                port_width_axis="u",
            )

    def add_feed_neck(feed_radial: float, feed_offset: float, feed_top_z: float) -> float:
        if params.get("board_edge_fed_l_feed_neck_enabled", 0.0) < 0.5:
            return feed_offset
        neck_l = params.get("board_edge_fed_l_feed_neck_length_mm", 0.0)
        if neck_l <= 1e-9:
            return feed_offset
        neck_w = params.get("board_edge_fed_l_feed_neck_width_mm", 0.14)
        neck_sign = 1.0 if params.get("board_edge_fed_l_feed_neck_side_sign", 1.0) >= 0.0 else -1.0
        port_offset = feed_offset + neck_sign * neck_l
        cross0, cross1 = sorted([feed_offset, port_offset])
        radial0, radial1 = sorted([side * feed_radial - neck_w / 2.0, side * feed_radial + neck_w / 2.0])
        if axis == "u":
            pts = rectangle_points(*center, angle_deg, radial0, radial1, cross0, cross1, feed_top_z)
        else:
            pts = rectangle_points(*center, angle_deg, cross0, cross1, radial0, radial1, feed_top_z)
        neck = polygon_sheet(hfss, f"{tag}_board_edge_fed_l_feed_neck", pts, "copper")
        metals.append(neck.name)
        return port_offset

    def add_series_match(feed_radial: float, feed_offset: float, feed_top_z: float) -> float | None:
        if params.get("board_edge_fed_l_series_match_enabled", 0.0) < 0.5:
            return None
        neck_l = params.get("board_edge_fed_l_feed_neck_length_mm", 0.0)
        if neck_l <= 1e-9:
            return None
        neck_sign = 1.0 if params.get("board_edge_fed_l_feed_neck_side_sign", 1.0) >= 0.0 else -1.0
        port_offset = feed_offset + neck_sign * neck_l
        series_w = params.get("board_edge_fed_l_series_match_width_mm", params.get("board_edge_fed_l_feed_neck_width_mm", 0.14))
        cross0, cross1 = sorted([feed_offset, port_offset])
        radial0, radial1 = sorted([side * feed_radial - series_w / 2.0, side * feed_radial + series_w / 2.0])
        if axis == "u":
            pts = rectangle_points(*center, angle_deg, radial0, radial1, cross0, cross1, feed_top_z)
            source = local_to_global(*center, angle_deg, side * feed_radial, port_offset, feed_top_z)
            load = local_to_global(*center, angle_deg, side * feed_radial, feed_offset, feed_top_z)
        else:
            pts = rectangle_points(*center, angle_deg, cross0, cross1, radial0, radial1, feed_top_z)
            source = local_to_global(*center, angle_deg, port_offset, side * feed_radial, feed_top_z)
            load = local_to_global(*center, angle_deg, feed_offset, side * feed_radial, feed_top_z)
        series_sheet = polygon_sheet(hfss, f"{tag}_board_edge_fed_l_series_match", pts, None)
        hfss.assign_lumped_rlc_to_sheet(
            series_sheet.name,
            start_direction=[source, load],
            name=f"{tag}_board_edge_fed_l_series_match",
            rlc_type="Serial",
            resistance=params.get("board_edge_fed_l_series_match_resistance_ohm", 0.0)
            if params.get("board_edge_fed_l_series_match_resistance_ohm", 0.0) > 0.0
            else None,
            capacitance=params.get("board_edge_fed_l_series_match_capacitance_pf", 0.0) * 1e-12
            if params.get("board_edge_fed_l_series_match_capacitance_pf", 0.0) > 0.0
            else None,
            inductance=params.get("board_edge_fed_l_series_match_inductance_nh", 0.0) * 1e-9
            if params.get("board_edge_fed_l_series_match_inductance_nh", 0.0) > 0.0
            else None,
        )
        return port_offset

    def add_port(feed_radial: float, feed_offset: float, feed_top_z: float) -> None:
        series_port_offset = add_series_match(feed_radial, feed_offset, feed_top_z)
        if series_port_offset is not None:
            port_offset = series_port_offset
            selected = source_feed_selected(params, port_name)
            if axis == "u":
                if selected:
                    metals.extend(
                        add_lumped_feed(
                            hfss,
                            port_name,
                            center,
                            angle_deg,
                            side * feed_radial,
                            port_offset,
                            feed_top_z,
                            0.0,
                            params,
                            pad=True,
                        )
                    )
                else:
                    add_lumped_switch_load(
                        hfss,
                        port_name,
                        center,
                        angle_deg,
                        side * feed_radial,
                        port_offset,
                        feed_top_z,
                        0.0,
                        params,
                    )
            else:
                if selected:
                    metals.extend(
                        add_lumped_feed(
                            hfss,
                            port_name,
                            center,
                            angle_deg,
                            port_offset,
                            side * feed_radial,
                            feed_top_z,
                            0.0,
                            params,
                            pad=True,
                            port_width_axis="u",
                        )
                    )
                else:
                    add_lumped_switch_load(
                        hfss,
                        port_name,
                        center,
                        angle_deg,
                        port_offset,
                        side * feed_radial,
                        feed_top_z,
                        0.0,
                        params,
                        port_width_axis="u",
                    )
            add_match(feed_radial, feed_offset, feed_top_z)
            return

        port_offset = add_feed_neck(feed_radial, feed_offset, feed_top_z)
        selected = source_feed_selected(params, port_name)
        if axis == "u":
            if selected:
                metals.extend(
                    add_lumped_feed(
                        hfss,
                        port_name,
                        center,
                        angle_deg,
                        side * feed_radial,
                        port_offset,
                        feed_top_z,
                        0.0,
                        params,
                        pad=False,
                    )
                )
            else:
                add_lumped_switch_load(
                    hfss,
                    port_name,
                    center,
                    angle_deg,
                    side * feed_radial,
                    port_offset,
                    feed_top_z,
                    0.0,
                    params,
                )
        else:
            if selected:
                metals.extend(
                    add_lumped_feed(
                        hfss,
                        port_name,
                        center,
                        angle_deg,
                        port_offset,
                        side * feed_radial,
                        feed_top_z,
                        0.0,
                        params,
                        pad=False,
                        port_width_axis="u",
                    )
                )
            else:
                add_lumped_switch_load(
                    hfss,
                    port_name,
                    center,
                    angle_deg,
                    port_offset,
                    side * feed_radial,
                    feed_top_z,
                    0.0,
                    params,
                    port_width_axis="u",
                )
        add_match(feed_radial, port_offset, feed_top_z)

    if monopole_enabled:
        height = params.get("board_edge_fed_monopole_height_mm", 4.8)
        width = params.get("board_edge_fed_monopole_width_mm", 0.24)
        gap = params.get("board_edge_fed_monopole_gap_mm", 0.80)
        offset = params.get("board_edge_fed_monopole_offset_mm", 0.0)
        top_load = params.get("board_edge_fed_monopole_topload_length_mm", 0.0)
        radial = edge + gap
        top_z = h + height
        cross0, cross1 = offset - width / 2.0, offset + width / 2.0
        if axis == "u":
            wall_pts = [
                local_to_global(*center, angle_deg, side * radial, cross0, h),
                local_to_global(*center, angle_deg, side * radial, cross1, h),
                local_to_global(*center, angle_deg, side * radial, cross1, top_z),
                local_to_global(*center, angle_deg, side * radial, cross0, top_z),
            ]
        else:
            wall_pts = [
                local_to_global(*center, angle_deg, cross0, side * radial, h),
                local_to_global(*center, angle_deg, cross1, side * radial, h),
                local_to_global(*center, angle_deg, cross1, side * radial, top_z),
                local_to_global(*center, angle_deg, cross0, side * radial, top_z),
            ]
        wall = polygon_sheet(hfss, f"{tag}_board_edge_fed_monopole_wall", wall_pts, "copper")
        metals.append(wall.name)
        if top_load > 1e-9:
            tan0, tan1 = sorted([offset, offset + top_load])
            radial0, radial1 = sorted([side * radial - width / 2.0, side * radial + width / 2.0])
            if axis == "u":
                pts = rectangle_points(*center, angle_deg, radial0, radial1, tan0, tan1, top_z)
            else:
                pts = rectangle_points(*center, angle_deg, tan0, tan1, radial0, radial1, top_z)
            top = polygon_sheet(hfss, f"{tag}_board_edge_fed_monopole_topload", pts, "copper")
            metals.append(top.name)
        add_port(radial, offset, h)

    if ifa_enabled:
        length = params.get("board_edge_fed_ifa_length_mm", 3.8)
        height = params.get("board_edge_fed_ifa_height_mm", 5.2)
        width = params.get("board_edge_fed_ifa_width_mm", 0.24)
        gap = params.get("board_edge_fed_ifa_gap_mm", 0.60)
        feed_offset = params.get("board_edge_fed_ifa_feed_offset_mm", 0.70)
        offset = params.get("board_edge_fed_ifa_offset_mm", 0.0)
        start = edge + gap
        stop = start + length
        feed_radial = start + feed_offset
        top_z = h + height
        radial0, radial1 = sorted([side * start, side * stop])
        cross0, cross1 = offset - width / 2.0, offset + width / 2.0
        if axis == "u":
            top_pts = rectangle_points(*center, angle_deg, radial0, radial1, cross0, cross1, top_z)
            short_pts = [
                local_to_global(*center, angle_deg, side * start, cross0, 0.0),
                local_to_global(*center, angle_deg, side * start, cross1, 0.0),
                local_to_global(*center, angle_deg, side * start, cross1, top_z),
                local_to_global(*center, angle_deg, side * start, cross0, top_z),
            ]
        else:
            top_pts = rectangle_points(*center, angle_deg, cross0, cross1, radial0, radial1, top_z)
            short_pts = [
                local_to_global(*center, angle_deg, cross0, side * start, 0.0),
                local_to_global(*center, angle_deg, cross1, side * start, 0.0),
                local_to_global(*center, angle_deg, cross1, side * start, top_z),
                local_to_global(*center, angle_deg, cross0, side * start, top_z),
            ]
        top_arm = polygon_sheet(hfss, f"{tag}_board_edge_fed_ifa_top_arm", top_pts, "copper")
        short_wall = polygon_sheet(hfss, f"{tag}_board_edge_fed_ifa_short_wall", short_pts, "copper")
        metals.extend([top_arm.name, short_wall.name])
        add_port(feed_radial, offset, top_z)

    return metals


def add_slotcoupled_ab_cancellation_network(
    hfss: Hfss,
    tag: str,
    center: tuple[float, float],
    angle_deg: float,
    params: dict,
    feed_z: float,
    feedline_a_v: float,
    feedline_b_u: float,
    half_feed_w: float,
    u_side_sign: float,
    v_side_sign: float,
) -> list[str]:
    if params.get("slot_coupled_ab_cancel_enabled", 0.0) < 0.5:
        return []
    coupling_l = params.get("slot_coupled_ab_cancel_coupling_length_mm", 1.60)
    trace_w = params.get("slot_coupled_ab_cancel_trace_width_mm", 0.12)
    gap = params.get("slot_coupled_ab_cancel_gap_mm", 0.08)
    phase_offset = params.get("slot_coupled_ab_cancel_phase_offset_mm", 2.00)
    side_sign = 1.0 if params.get("slot_coupled_ab_cancel_side_sign", 1.0) >= 0.0 else -1.0
    z = feed_z + params.get("slot_coupled_ab_cancel_z_offset_mm", 0.0)
    overlap = min(0.08, max(0.03, trace_w / 2.0))

    uq = u_side_sign * side_sign
    vq = v_side_sign * side_sign
    coupling_edge = half_feed_w + gap + trace_w / 2.0
    a_center_u = uq * phase_offset
    a_center_v = feedline_a_v + vq * coupling_edge
    b_center_u = feedline_b_u + uq * coupling_edge
    b_center_v = vq * phase_offset

    metals = []
    a_pad = polygon_sheet(
        hfss,
        f"{tag}_slotcoupled_ab_cancel_a_coupler",
        rotated_rectangle_points(*center, angle_deg, a_center_u, a_center_v, 0.0, coupling_l, trace_w, z),
        "copper",
    )
    b_pad = polygon_sheet(
        hfss,
        f"{tag}_slotcoupled_ab_cancel_b_coupler",
        rotated_rectangle_points(*center, angle_deg, b_center_u, b_center_v, 90.0, coupling_l, trace_w, z),
        "copper",
    )
    metals.extend([a_pad.name, b_pad.name])

    a_inner_u = uq * (phase_offset - coupling_l / 2.0 + overlap)
    a_inner_v = a_center_v
    b_inner_u = b_center_u
    b_inner_v = vq * (phase_offset - coupling_l / 2.0 + overlap)
    du = b_inner_u - a_inner_u
    dv = b_inner_v - a_inner_v
    connector_l = math.hypot(du, dv)
    if connector_l > trace_w:
        connector = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_ab_cancel_phase_line",
            rotated_rectangle_points(
                *center,
                angle_deg,
                (a_inner_u + b_inner_u) / 2.0,
                (a_inner_v + b_inner_v) / 2.0,
                math.degrees(math.atan2(dv, du)),
                connector_l + 2.0 * overlap,
                trace_w,
                z,
            ),
            "copper",
        )
        metals.append(connector.name)
    return metals


def add_dualpol_parasitic_patch(hfss: Hfss, tag: str, center: tuple[float, float], angle: float, params: dict) -> list[str]:
    if not has_stacked_parasitic(params):
        return []
    h = params["substrate_h_mm"]
    parasitic_z = h + params.get("air_gap_mm", 0.0)
    parasitic_offset = local_to_global(
        center[0],
        center[1],
        angle,
        params.get("parasitic_offset_u_mm", 0.0),
        params.get("parasitic_offset_v_mm", 0.0),
        parasitic_z,
    )
    parasitic = polygon_sheet(
        hfss,
        f"{tag}_dualpol_stacked_parasitic_patch",
        patch_points(
            parasitic_offset[0],
            parasitic_offset[1],
            angle + params.get("parasitic_rotation_deg", 0.0),
            params["parasitic_side_mm"],
            params.get("parasitic_corner_cut_mm", 0.0),
            parasitic_z,
        ),
    )
    return [parasitic.name]


def add_dualfeed_element(hfss: Hfss, tag: str, center: tuple[float, float], angle: float, params: dict, hybrid_traces: bool = False) -> list[str]:
    metals = []
    h = params["substrate_h_mm"]
    patch = polygon_sheet(
        hfss,
        f"{tag}_dualfeed_square_patch",
        patch_points(*center, angle, params["patch_side_mm"], 0.0, h),
    )
    metals.append(patch.name)
    metals.extend(add_dualpol_parasitic_patch(hfss, tag, center, angle, params))
    metals.extend(add_weak_coupling_open_line(hfss, tag, center, angle, params))
    f_a = params.get("feed_offset_a_mm", params["feed_offset_u_mm"])
    f_b = params.get("feed_offset_b_mm", params["feed_offset_u_mm"])
    if params.get("microstrip_feed_enabled", 0.0) >= 0.5:
        u_side_sign = mirrored_feed_side_sign(center, "u", params)
        v_side_sign = mirrored_feed_side_sign(center, "v", params)
        metals += add_microstrip_edge_feed(hfss, f"P{tag[-1]}A", center, angle, "u", params, hybrid_outputs=hybrid_traces, side_sign=u_side_sign)
        metals += add_microstrip_edge_feed(hfss, f"P{tag[-1]}B", center, angle, "v", params, hybrid_outputs=hybrid_traces, side_sign=v_side_sign)
        metals += add_neutralization_branch(hfss, tag, center, angle, params, u_side_sign, v_side_sign)
    else:
        metals += add_lumped_feed(hfss, f"P{tag[-1]}A", center, angle, f_a, 0.0, h, 0.0, params)
        metals += add_lumped_feed(hfss, f"P{tag[-1]}B", center, angle, 0.0, f_b, h, 0.0, params)
        metals += add_weak_coupling_open_line(hfss, tag, center, angle, params)
        add_via_fence(hfss, tag, center, angle, params)
    if hybrid_traces and params.get("microstrip_feed_enabled", 0.0) < 0.5:
        w = params.get("hybrid_trace_width_mm", 0.32)
        gap = params.get("hybrid_trace_gap_mm", 0.55)
        f = max(f_a, f_b)
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


def add_dualpol_slotcoupled_element(hfss: Hfss, tag: str, center: tuple[float, float], angle: float, params: dict) -> tuple[list[str], list[str]]:
    metals = []
    slots = []
    h = params["substrate_h_mm"]
    feed_z_a = -params.get("feed_substrate_h_mm", 0.254)
    feed_z_b = feed_z_a - params.get("slot_coupled_b_feed_layer_offset_mm", 0.0)
    patch = polygon_sheet(
        hfss,
        f"{tag}_dualpol_slotcoupled_patch",
        patch_points(*center, angle, params["patch_side_mm"], 0.0, h),
    )
    add_slotcoupled_horizon_loop(hfss, tag, patch.name, center, angle, params)
    add_slotcoupled_patch_slit(hfss, tag, patch.name, center, angle, params)
    metals.append(patch.name)
    metals.extend(add_slotcoupled_edge_radiators(hfss, tag, center, angle, params))
    metals.extend(add_dualpol_parasitic_patch(hfss, tag, center, angle, params))

    aperture_w = params["slot_coupled_aperture_width_mm"]
    aperture_a_u = params.get("slot_coupled_offset_a_mm", 0.0)
    aperture_a_v = params.get("slot_coupled_aperture_center_a_v_mm", 0.0)
    aperture_b_u = params.get("slot_coupled_aperture_center_b_u_mm", 0.0)
    aperture_b_v = params.get("slot_coupled_offset_b_mm", 0.0)
    aperture_a = polygon_sheet(
        hfss,
        f"{tag}_slotcoupled_a_aperture",
        rectangle_points(
            *center,
            angle,
            aperture_a_u - aperture_w / 2.0,
            aperture_a_u + aperture_w / 2.0,
            aperture_a_v - params["slot_coupled_aperture_length_a_mm"] / 2.0,
            aperture_a_v + params["slot_coupled_aperture_length_a_mm"] / 2.0,
            0.0,
        ),
        "vacuum",
    )
    aperture_b = polygon_sheet(
        hfss,
        f"{tag}_slotcoupled_b_aperture",
        rectangle_points(
            *center,
            angle,
            aperture_b_u - params["slot_coupled_aperture_length_b_mm"] / 2.0,
            aperture_b_u + params["slot_coupled_aperture_length_b_mm"] / 2.0,
            aperture_b_v - aperture_w / 2.0,
            aperture_b_v + aperture_w / 2.0,
            0.0,
        ),
        "vacuum",
    )
    slots.extend([aperture_a.name, aperture_b.name])

    half_l = params["slot_coupled_feedline_length_mm"] / 2.0
    half_w = params["slot_coupled_feedline_width_mm"] / 2.0
    feedline_a_v = params.get("slot_coupled_feedline_offset_a_v_mm", 0.0)
    feedline_b_u = params.get("slot_coupled_feedline_offset_b_u_mm", 0.0)
    u_side_sign = mirrored_feed_side_sign(center, "u", params)
    v_side_sign = mirrored_feed_side_sign(center, "v", params)

    if params.get("slot_coupled_underfeed_neutralizer_enabled", 0.0) >= 0.5:
        neutralizer = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_underfeed_neutralizer",
            rotated_rectangle_points(
                *center,
                angle,
                u_side_sign * params.get("slot_coupled_underfeed_neutralizer_offset_mm", 1.20),
                v_side_sign * params.get("slot_coupled_underfeed_neutralizer_offset_mm", 1.20),
                -45.0 * u_side_sign * v_side_sign,
                params.get("slot_coupled_underfeed_neutralizer_length_mm", 2.2),
                params.get("slot_coupled_underfeed_neutralizer_width_mm", 0.12),
                feed_z_a + params.get("slot_coupled_underfeed_neutralizer_z_offset_mm", 0.06),
            ),
            "copper",
        )
        metals.append(neutralizer.name)

    def vertical_local_sheet(name: str, u0: float, u1: float, v: float, z0: float, z1: float) -> str:
        pts = [
            local_to_global(*center, angle, u0, v, z0),
            local_to_global(*center, angle, u1, v, z0),
            local_to_global(*center, angle, u1, v, z1),
            local_to_global(*center, angle, u0, v, z1),
        ]
        return polygon_sheet(hfss, name, pts, "copper").name

    if params.get("slot_coupled_a_neck_enabled", 0.0) >= 0.5:
        neck_l = params.get("slot_coupled_a_neck_length_mm", 2.2)
        neck_w = params.get("slot_coupled_a_neck_width_mm", params["slot_coupled_feedline_width_mm"])
        neck_half_l = neck_l / 2.0
        neck_half_w = neck_w / 2.0
        overlap = 0.03
        for suffix, u0, u1, v0, v1 in [
            ("neg", -half_l, -neck_half_l + overlap, feedline_a_v - half_w, feedline_a_v + half_w),
            ("neck", -neck_half_l, neck_half_l, feedline_a_v - neck_half_w, feedline_a_v + neck_half_w),
            ("pos", neck_half_l - overlap, half_l, feedline_a_v - half_w, feedline_a_v + half_w),
        ]:
            line_a = polygon_sheet(
                hfss,
                f"{tag}_slotcoupled_a_underside_feedline_{suffix}",
                rectangle_points(*center, angle, u0, u1, v0, v1, feed_z_a),
                "copper",
            )
            metals.append(line_a.name)
    else:
        line_a = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_a_underside_feedline",
            rectangle_points(*center, angle, -half_l, half_l, feedline_a_v - half_w, feedline_a_v + half_w, feed_z_a),
            "copper",
        )
        metals.append(line_a.name)
    a_res_len = params.get("slot_coupled_a_resonator_length_mm", 0.0)
    a_res_w = params.get("slot_coupled_a_resonator_width_mm", 0.0)
    if a_res_len > 1e-9 and a_res_w > half_w * 2.0 + 1e-9:
        a_resonator = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_a_center_resonator",
            rectangle_points(
                *center,
                angle,
                -a_res_len / 2.0,
                a_res_len / 2.0,
                feedline_a_v - a_res_w / 2.0,
                feedline_a_v + a_res_w / 2.0,
                feed_z_a,
            ),
            "copper",
        )
        metals.append(a_resonator.name)
    if params.get("slot_coupled_bridge_enabled", 0.0) >= 0.5:
        bridge_gap = params.get("slot_coupled_bridge_gap_mm", 1.10)
        bridge_offset = params.get("slot_coupled_bridge_offset_mm", 0.0)
        bridge_half_w = params.get("slot_coupled_bridge_width_mm", params["slot_coupled_feedline_width_mm"]) / 2.0
        resonator_half_w = max(
            params.get("slot_coupled_bridge_resonator_width_mm", 0.0),
            params.get("slot_coupled_bridge_width_mm", params["slot_coupled_feedline_width_mm"]),
        ) / 2.0
        bridge_overhang = params.get("slot_coupled_bridge_overhang_mm", 0.0)
        bridge_z = feed_z_b - bridge_offset
        line_b_neg = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_b_underside_feedline_neg",
            rectangle_points(*center, angle, feedline_b_u - half_w, feedline_b_u + half_w, -half_l, -bridge_gap / 2.0, feed_z_b),
            "copper",
        )
        line_b_pos = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_b_underside_feedline_pos",
            rectangle_points(*center, angle, feedline_b_u - half_w, feedline_b_u + half_w, bridge_gap / 2.0, half_l, feed_z_b),
            "copper",
        )
        bridge = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_b_center_bridge",
            rectangle_points(
                *center,
                angle,
                feedline_b_u - resonator_half_w,
                feedline_b_u + resonator_half_w,
                -bridge_gap / 2.0 - bridge_overhang,
                bridge_gap / 2.0 + bridge_overhang,
                bridge_z,
            ),
            "copper",
        )
        metals.extend(
            [
                line_b_neg.name,
                line_b_pos.name,
                bridge.name,
                vertical_local_sheet(
                    f"{tag}_slotcoupled_b_bridge_via_neg",
                    feedline_b_u - bridge_half_w,
                    feedline_b_u + bridge_half_w,
                    -bridge_gap / 2.0,
                    feed_z_b,
                    bridge_z,
                ),
                vertical_local_sheet(
                    f"{tag}_slotcoupled_b_bridge_via_pos",
                    feedline_b_u - bridge_half_w,
                    feedline_b_u + bridge_half_w,
                    bridge_gap / 2.0,
                    feed_z_b,
                    bridge_z,
                ),
            ]
        )
    else:
        line_b = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_b_underside_feedline",
            rectangle_points(*center, angle, feedline_b_u - half_w, feedline_b_u + half_w, -half_l, half_l, feed_z_b),
            "copper",
        )
        metals.append(line_b.name)
    if params.get("slot_coupled_step_enabled", 0.0) >= 0.5:
        step_l = params.get("slot_coupled_step_length_mm", 0.0)
        step_w = params.get("slot_coupled_step_width_mm", params["slot_coupled_feedline_width_mm"])
        if step_l > 1e-9 and step_w > params["slot_coupled_feedline_width_mm"] + 1e-9:
            step_a_u0 = u_side_sign * (half_l - step_l)
            step_a_u1 = u_side_sign * half_l
            step_a = polygon_sheet(
                hfss,
                f"{tag}_slotcoupled_a_port_step",
                rectangle_points(
                    *center,
                    angle,
                    min(step_a_u0, step_a_u1),
                    max(step_a_u0, step_a_u1),
                    feedline_a_v - step_w / 2.0,
                    feedline_a_v + step_w / 2.0,
                    feed_z_a,
                ),
                "copper",
            )
            step_b_v0 = v_side_sign * (half_l - step_l)
            step_b_v1 = v_side_sign * half_l
            step_b = polygon_sheet(
                hfss,
                f"{tag}_slotcoupled_b_port_step",
                rectangle_points(
                    *center,
                    angle,
                    feedline_b_u - step_w / 2.0,
                    feedline_b_u + step_w / 2.0,
                    min(step_b_v0, step_b_v1),
                    max(step_b_v0, step_b_v1),
                    feed_z_b,
                ),
                "copper",
            )
            metals.extend([step_a.name, step_b.name])

    def add_stub_pair(suffix: str, stub_l: float, stub_w: float, stub_offset: float, stub_side_value: float) -> None:
        if stub_l <= 1e-9 or stub_w <= 1e-9:
            return
        stub_side = 1.0 if stub_side_value >= 0.0 else -1.0
        stub_a_u = u_side_sign * stub_offset
        if stub_side >= 0.0:
            stub_a_v0 = feedline_a_v + half_w - 0.03
            stub_a_v1 = feedline_a_v + half_w + stub_l
        else:
            stub_a_v0 = feedline_a_v - half_w - stub_l
            stub_a_v1 = feedline_a_v - half_w + 0.03
        stub_a = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_a_{suffix}",
            rectangle_points(*center, angle, stub_a_u - stub_w / 2.0, stub_a_u + stub_w / 2.0, stub_a_v0, stub_a_v1, feed_z_a),
            "copper",
        )
        stub_b_v = v_side_sign * stub_offset
        if stub_side >= 0.0:
            stub_b_u0 = feedline_b_u + half_w - 0.03
            stub_b_u1 = feedline_b_u + half_w + stub_l
        else:
            stub_b_u0 = feedline_b_u - half_w - stub_l
            stub_b_u1 = feedline_b_u - half_w + 0.03
        stub_b = polygon_sheet(
            hfss,
            f"{tag}_slotcoupled_b_{suffix}",
            rectangle_points(*center, angle, stub_b_u0, stub_b_u1, stub_b_v - stub_w / 2.0, stub_b_v + stub_w / 2.0, feed_z_b),
            "copper",
        )
        metals.extend([stub_a.name, stub_b.name])

    if params.get("slot_coupled_stub_enabled", 0.0) >= 0.5:
        add_stub_pair(
            "open_stub",
            params.get("slot_coupled_stub_length_mm", 0.0),
            params.get("slot_coupled_stub_width_mm", 0.25),
            params.get("slot_coupled_stub_offset_mm", 2.0),
            params.get("slot_coupled_stub_side_sign", 1.0),
        )
    if params.get("slot_coupled_stub2_enabled", 0.0) >= 0.5:
        add_stub_pair(
            "open_stub2",
            params.get("slot_coupled_stub2_length_mm", 0.0),
            params.get("slot_coupled_stub2_width_mm", 0.25),
            params.get("slot_coupled_stub2_offset_mm", 3.0),
            params.get("slot_coupled_stub2_side_sign", -1.0),
        )
    metals.extend(
        add_slotcoupled_ab_cancellation_network(
            hfss,
            tag,
            center,
            angle,
            params,
            feed_z_a,
            feedline_a_v,
            feedline_b_u,
            half_w,
            u_side_sign,
            v_side_sign,
        )
    )
    add_slotcoupled_shield_vias(hfss, tag, center, angle, params)
    switch_enabled = params.get("rf_switch_equiv_enabled", 0.0) >= 0.5
    active_pol = int(round(params.get("rf_switch_active_pol", 0.0)))
    a_name = f"P{tag[-1]}A"
    b_name = f"P{tag[-1]}B"
    a_is_port = (not switch_enabled or active_pol == 0) and source_feed_selected(params, a_name)
    b_is_port = (not switch_enabled or active_pol == 1) and source_feed_selected(params, b_name)
    if a_is_port:
        metals += add_lumped_feed(hfss, a_name, center, angle, u_side_sign * half_l, feedline_a_v, 0.0, feed_z_a, params, pad=False)
    else:
        add_lumped_switch_load(hfss, a_name, center, angle, u_side_sign * half_l, feedline_a_v, 0.0, feed_z_a, params)
    if b_is_port:
        metals += add_lumped_feed(hfss, b_name, center, angle, feedline_b_u, v_side_sign * half_l, 0.0, feed_z_b, params, pad=False, port_width_axis="u")
    else:
        add_lumped_switch_load(hfss, b_name, center, angle, feedline_b_u, v_side_sign * half_l, 0.0, feed_z_b, params, port_width_axis="u")
    return metals, slots


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
    stacked_parasitic = has_stacked_parasitic(params)
    slotcoupled = has_dualpol_slotcoupled(params)
    top_height = params["substrate_h_mm"] + 2.0 * params["copper_t_mm"]
    if stacked_parasitic:
        top_height += params.get("air_gap_mm", 0.0)
        top_height += params["copper_t_mm"]
    if slotcoupled:
        top_height += params.get("feed_substrate_h_mm", 0.254) + params["copper_t_mm"]
    if params.get("weak_coupling_open_line_enabled", 0.0) >= 0.5:
        top_height = max(
            top_height,
            params["substrate_h_mm"] + params.get("weak_coupling_open_line_gap_mm", 0.08) + params["copper_t_mm"],
        )
    if params.get("slot_coupled_edge_wall_enabled", 0.0) >= 0.5:
        top_height = max(
            top_height,
            params["substrate_h_mm"] + params.get("slot_coupled_edge_wall_height_mm", 2.0) + params["copper_t_mm"],
        )
    if params.get("slot_coupled_board_edge_ifa_enabled", 0.0) >= 0.5:
        top_height = max(
            top_height,
            params["substrate_h_mm"] + params.get("slot_coupled_board_edge_ifa_height_mm", 3.8) + params["copper_t_mm"],
        )
    if params.get("slot_coupled_folded_edge_arm_enabled", 0.0) >= 0.5:
        top_height = max(
            top_height,
            params["substrate_h_mm"] + params.get("slot_coupled_folded_edge_arm_height_mm", 5.2) + params["copper_t_mm"],
        )
    if params.get("board_edge_fed_monopole_enabled", 0.0) >= 0.5:
        top_height = max(
            top_height,
            params["substrate_h_mm"] + params.get("board_edge_fed_monopole_height_mm", 4.8) + params["copper_t_mm"],
        )
    if params.get("board_edge_fed_ifa_enabled", 0.0) >= 0.5:
        top_height = max(
            top_height,
            params["substrate_h_mm"] + params.get("board_edge_fed_ifa_height_mm", 5.2) + params["copper_t_mm"],
        )
    if top_height > params["total_height_limit_mm"]:
        raise ValueError(f"Total height {top_height:.3f} mm exceeds {params['total_height_limit_mm']:.3f} mm")
    if params["ground_radius_mm"] > params["board_diameter_mm"] / 2.0:
        raise ValueError("Ground radius must stay inside board")
    board_radius = params["board_diameter_mm"] / 2.0
    center_radius = params["element_spacing_mm"] / math.sqrt(2.0)
    max_side = max(params["patch_side_mm"], params.get("parasitic_side_mm", params["patch_side_mm"]) if stacked_parasitic else params["patch_side_mm"])
    if center_radius + max_side / math.sqrt(2.0) > board_radius - 0.25:
        raise ValueError("Patch corner too close to board edge")
    if slotcoupled:
        feed_h = params.get("feed_substrate_h_mm", 0.254)
        aperture_len_a = params.get("slot_coupled_aperture_length_a_mm", 0.0)
        aperture_len_b = params.get("slot_coupled_aperture_length_b_mm", 0.0)
        aperture_w = params.get("slot_coupled_aperture_width_mm", 0.0)
        feed_len = params.get("slot_coupled_feedline_length_mm", 0.0)
        feed_w = params.get("slot_coupled_feedline_width_mm", 0.0)
        half_patch = params["patch_side_mm"] / 2.0
        aperture_a_u = params.get("slot_coupled_offset_a_mm", 0.0)
        aperture_a_v = params.get("slot_coupled_aperture_center_a_v_mm", 0.0)
        aperture_b_u = params.get("slot_coupled_aperture_center_b_u_mm", 0.0)
        aperture_b_v = params.get("slot_coupled_offset_b_mm", 0.0)
        feedline_a_v = params.get("slot_coupled_feedline_offset_a_v_mm", 0.0)
        feedline_b_u = params.get("slot_coupled_feedline_offset_b_u_mm", 0.0)
        b_layer_offset = params.get("slot_coupled_b_feed_layer_offset_mm", 0.0)
        bridge_enabled = params.get("slot_coupled_bridge_enabled", 0.0) >= 0.5
        bridge_gap = params.get("slot_coupled_bridge_gap_mm", 1.10)
        bridge_offset = params.get("slot_coupled_bridge_offset_mm", 0.0)
        bridge_w = params.get("slot_coupled_bridge_width_mm", feed_w)
        bridge_res_w = params.get("slot_coupled_bridge_resonator_width_mm", 0.0)
        bridge_overhang = params.get("slot_coupled_bridge_overhang_mm", 0.0)
        a_res_len = params.get("slot_coupled_a_resonator_length_mm", 0.0)
        a_res_w = params.get("slot_coupled_a_resonator_width_mm", 0.0)
        shield_enabled = params.get("slot_coupled_shield_via_enabled", 0.0) >= 0.5
        shield_count = max(1, int(round(params.get("slot_coupled_shield_via_count", 1.0))))
        shield_radius = params.get("slot_coupled_shield_via_radius_mm", 0.06)
        shield_offset = params.get("slot_coupled_shield_via_offset_mm", 0.68)
        shield_pitch = params.get("slot_coupled_shield_via_pitch_mm", 0.42)
        shield_top_gap = params.get("slot_coupled_shield_via_top_gap_mm", 0.03)
        a_neck_enabled = params.get("slot_coupled_a_neck_enabled", 0.0) >= 0.5
        a_neck_len = params.get("slot_coupled_a_neck_length_mm", 2.2)
        a_neck_w = params.get("slot_coupled_a_neck_width_mm", 0.30)
        neutralizer_enabled = params.get("slot_coupled_underfeed_neutralizer_enabled", 0.0) >= 0.5
        neutralizer_len = params.get("slot_coupled_underfeed_neutralizer_length_mm", 2.2)
        neutralizer_w = params.get("slot_coupled_underfeed_neutralizer_width_mm", 0.12)
        neutralizer_offset = params.get("slot_coupled_underfeed_neutralizer_offset_mm", 1.20)
        neutralizer_z_offset = params.get("slot_coupled_underfeed_neutralizer_z_offset_mm", 0.06)
        patch_slit_enabled = params.get("slot_coupled_patch_slit_enabled", 0.0) >= 0.5
        patch_slit_len = params.get("slot_coupled_patch_slit_length_mm", 3.0)
        patch_slit_w = params.get("slot_coupled_patch_slit_width_mm", 0.10)
        patch_slit_offset_u = params.get("slot_coupled_patch_slit_offset_u_mm", 0.0)
        patch_slit_offset_v = params.get("slot_coupled_patch_slit_offset_v_mm", 0.0)
        horizon_loop_enabled = params.get("slot_coupled_horizon_loop_enabled", 0.0) >= 0.5
        horizon_loop_inner = params.get("slot_coupled_horizon_loop_inner_side_mm", 0.0)
        horizon_loop_offset_u = params.get("slot_coupled_horizon_loop_offset_u_mm", 0.0)
        horizon_loop_offset_v = params.get("slot_coupled_horizon_loop_offset_v_mm", 0.0)
        edge_arm_enabled = params.get("slot_coupled_edge_arm_enabled", 0.0) >= 0.5
        edge_arm_len = params.get("slot_coupled_edge_arm_length_mm", 2.4)
        edge_arm_w = params.get("slot_coupled_edge_arm_width_mm", 0.30)
        edge_arm_offset = params.get("slot_coupled_edge_arm_offset_mm", 0.0)
        edge_arm_gap = params.get("slot_coupled_edge_arm_gap_mm", 0.0)
        edge_wall_enabled = params.get("slot_coupled_edge_wall_enabled", 0.0) >= 0.5
        edge_wall_h = params.get("slot_coupled_edge_wall_height_mm", 2.0)
        edge_wall_w = params.get("slot_coupled_edge_wall_width_mm", 0.50)
        edge_wall_offset = params.get("slot_coupled_edge_wall_offset_mm", 0.0)
        board_ifa_enabled = params.get("slot_coupled_board_edge_ifa_enabled", 0.0) >= 0.5
        board_ifa_len = params.get("slot_coupled_board_edge_ifa_length_mm", 4.6)
        board_ifa_w = params.get("slot_coupled_board_edge_ifa_width_mm", 0.35)
        board_ifa_h = params.get("slot_coupled_board_edge_ifa_height_mm", 3.8)
        board_ifa_gap = params.get("slot_coupled_board_edge_ifa_gap_mm", 0.15)
        board_ifa_offset = params.get("slot_coupled_board_edge_ifa_offset_mm", 0.0)
        folded_edge_enabled = params.get("slot_coupled_folded_edge_arm_enabled", 0.0) >= 0.5
        folded_radial_len = params.get("slot_coupled_folded_edge_arm_radial_length_mm", 1.8)
        folded_tangent_len = params.get("slot_coupled_folded_edge_arm_tangent_length_mm", 5.5)
        folded_w = params.get("slot_coupled_folded_edge_arm_width_mm", 0.30)
        folded_h = params.get("slot_coupled_folded_edge_arm_height_mm", 5.2)
        folded_offset = params.get("slot_coupled_folded_edge_arm_offset_mm", 0.0)
        folded_gap = params.get("slot_coupled_folded_edge_arm_gap_mm", 0.0)
        ab_cancel_enabled = params.get("slot_coupled_ab_cancel_enabled", 0.0) >= 0.5
        ab_cancel_l = params.get("slot_coupled_ab_cancel_coupling_length_mm", 1.60)
        ab_cancel_w = params.get("slot_coupled_ab_cancel_trace_width_mm", 0.12)
        ab_cancel_gap = params.get("slot_coupled_ab_cancel_gap_mm", 0.08)
        ab_cancel_phase_offset = params.get("slot_coupled_ab_cancel_phase_offset_mm", 2.00)
        ab_cancel_z_offset = params.get("slot_coupled_ab_cancel_z_offset_mm", 0.0)
        switch_enabled = params.get("rf_switch_equiv_enabled", 0.0) >= 0.5
        switch_active_pol = int(round(params.get("rf_switch_active_pol", 0.0)))
        switch_off_r = params.get("rf_switch_off_resistance_ohm", 50.0)
        switch_off_c = params.get("rf_switch_off_capacitance_pf", 0.08)
        switch_off_l = params.get("rf_switch_off_inductance_nh", 0.0)
        stub_enabled = params.get("slot_coupled_stub_enabled", 0.0) >= 0.5
        stub_len = params.get("slot_coupled_stub_length_mm", 0.0)
        stub_w = params.get("slot_coupled_stub_width_mm", 0.25)
        stub_offset = params.get("slot_coupled_stub_offset_mm", 2.0)
        stub2_enabled = params.get("slot_coupled_stub2_enabled", 0.0) >= 0.5
        stub2_len = params.get("slot_coupled_stub2_length_mm", 0.0)
        stub2_w = params.get("slot_coupled_stub2_width_mm", 0.25)
        stub2_offset = params.get("slot_coupled_stub2_offset_mm", 3.0)
        step_enabled = params.get("slot_coupled_step_enabled", 0.0) >= 0.5
        step_len = params.get("slot_coupled_step_length_mm", 0.0)
        step_w = params.get("slot_coupled_step_width_mm", feed_w)
        if feed_h <= 0.0 or aperture_len_a <= 0.0 or aperture_len_b <= 0.0 or aperture_w <= 0.0 or feed_len <= 0.0 or feed_w <= 0.0:
            raise ValueError("Dual-polarized slot-coupled feed dimensions must be positive")
        if b_layer_offset < 0.0 or b_layer_offset > 0.45:
            raise ValueError("Dual-polarized B feed layer offset must be between 0 and 0.45 mm")
        if switch_enabled:
            if switch_active_pol not in {0, 1}:
                raise ValueError("RF switch active polarization must be 0 for A_ON or 1 for B_ON")
            if switch_off_r <= 0.0 or switch_off_c < 0.0 or switch_off_l < 0.0:
                raise ValueError("RF switch off-state RLC values must be positive/non-negative")
        if bridge_enabled and (
            bridge_gap <= feed_w + 0.10
            or bridge_gap >= feed_len - 0.50
            or bridge_offset <= 0.0
            or bridge_offset > 0.35
            or bridge_w <= 0.0
            or bridge_res_w < 0.0
            or bridge_overhang < 0.0
            or bridge_gap + 2.0 * bridge_overhang >= feed_len - 0.50
        ):
            raise ValueError("Dual-polarized feed bridge needs a positive offset and a center gap wider than the feedline")
        if a_res_len < 0.0 or a_res_w < 0.0:
            raise ValueError("Dual-polarized A feed center resonator dimensions must be non-negative")
        if a_res_len > 1e-9 or a_res_w > 1e-9:
            if a_res_len <= 0.0 or a_res_w <= feed_w or a_res_len >= feed_len - 0.50:
                raise ValueError("Dual-polarized A feed center resonator must be wider than the feedline and fit under the patch")
            if bridge_enabled and abs(feedline_a_v) + a_res_w / 2.0 >= bridge_gap / 2.0 - 0.05:
                raise ValueError("Dual-polarized A feed center resonator must stay inside the B-feed bridge gap")
        if shield_enabled:
            max_shield_offset = shield_offset + (shield_count - 1) * shield_pitch
            slot_clear = aperture_w / 2.0 + shield_radius + 0.05
            feed_clear = feed_w / 2.0 + shield_radius + 0.05
            if shield_count < 1 or shield_count > 3:
                raise ValueError("Dual-polarized slot-coupled shield via count must be between 1 and 3")
            if shield_radius <= 0.0 or shield_radius > 0.12 or shield_offset <= 0.0 or shield_pitch < 0.0:
                raise ValueError("Dual-polarized slot-coupled shield via dimensions must be positive and manufacturable")
            if params.get("slot_coupled_shield_via_grounded", 1.0) < 0.5 and (shield_top_gap <= 0.0 or shield_top_gap > feed_h - 0.02):
                raise ValueError("Floating slot-coupled shield vias need a positive top gap inside the feed dielectric")
            if shield_offset <= max(slot_clear, feed_clear):
                raise ValueError("Dual-polarized slot-coupled shield vias must clear the cross apertures and feedlines")
            if max_shield_offset + shield_radius > half_patch - 0.35:
                raise ValueError("Dual-polarized slot-coupled shield vias must stay under the patch ground region")
        if a_neck_enabled:
            if a_neck_len <= 0.20 or a_neck_len >= feed_len - 0.50:
                raise ValueError("Dual-polarized A feed neck must fit inside the feedline")
            if a_neck_w <= 0.08 or a_neck_w >= feed_w:
                raise ValueError("Dual-polarized A feed neck must be narrower than the main feedline")
        if neutralizer_enabled:
            if neutralizer_len <= 0.20 or neutralizer_w <= 0.02 or neutralizer_offset <= 0.0:
                raise ValueError("Dual-polarized underfeed neutralizer dimensions must be positive")
            if neutralizer_z_offset <= 0.0 or neutralizer_z_offset >= feed_h - 0.02:
                raise ValueError("Dual-polarized underfeed neutralizer must stay inside the feed dielectric")
            half_diag_extent = (neutralizer_len + neutralizer_w) / (2.0 * math.sqrt(2.0))
            if neutralizer_offset + half_diag_extent > half_patch - 0.35:
                raise ValueError("Dual-polarized underfeed neutralizer must stay under the patch")
        if patch_slit_enabled:
            if patch_slit_len <= 0.20 or patch_slit_w <= 0.02 or patch_slit_w >= 0.45:
                raise ValueError("Dual-polarized patch decoupling slit dimensions must be positive and narrow")
            slit_extent = max(abs(patch_slit_offset_u), abs(patch_slit_offset_v)) + (patch_slit_len + patch_slit_w) / 2.0
            if slit_extent > half_patch - 0.35:
                raise ValueError("Dual-polarized patch decoupling slit must stay inside the patch")
        if horizon_loop_enabled:
            if horizon_loop_inner <= 0.0 or horizon_loop_inner >= params["patch_side_mm"] - 1.0:
                raise ValueError("Dual-polarized horizon loop opening must leave a meaningful frame width")
            loop_frame = (params["patch_side_mm"] - horizon_loop_inner) / 2.0
            if loop_frame < 0.65 or loop_frame > half_patch - 0.25:
                raise ValueError("Dual-polarized horizon loop frame width must stay manufacturable")
            loop_extent = max(abs(horizon_loop_offset_u), abs(horizon_loop_offset_v)) + horizon_loop_inner / 2.0
            if loop_extent > half_patch - 0.25:
                raise ValueError("Dual-polarized horizon loop must stay inside the patch footprint")
        if edge_arm_enabled:
            if edge_arm_len <= 0.20 or edge_arm_w <= 0.04 or edge_arm_w > 0.80 or edge_arm_gap < 0.0:
                raise ValueError("Dual-polarized edge arm dimensions must be positive and manufacturable")
            if abs(edge_arm_offset) + edge_arm_w / 2.0 > half_patch - 0.35:
                raise ValueError("Dual-polarized edge arm must attach within the patch edge span")
            if center_radius + half_patch + edge_arm_gap + edge_arm_len > board_radius - 0.25:
                raise ValueError("Dual-polarized edge arm must stay inside the board edge")
        if edge_wall_enabled:
            if edge_wall_h <= 0.20 or edge_wall_w <= 0.04 or edge_wall_w > 1.20:
                raise ValueError("Dual-polarized edge wall dimensions must be positive and manufacturable")
            if params["substrate_h_mm"] + edge_wall_h + params["copper_t_mm"] > params["total_height_limit_mm"]:
                raise ValueError("Dual-polarized edge wall exceeds the total height limit")
            if abs(edge_wall_offset) + edge_wall_w / 2.0 > half_patch - 0.35:
                raise ValueError("Dual-polarized edge wall must attach within the patch edge span")
        if board_ifa_enabled:
            if board_ifa_len <= 0.50 or board_ifa_w <= 0.06 or board_ifa_w > 0.90:
                raise ValueError("Board-edge IFA dimensions must be positive and manufacturable")
            if board_ifa_h <= 0.50:
                raise ValueError("Board-edge IFA height must be positive")
            if board_ifa_gap < 0.05:
                raise ValueError("Board-edge IFA needs an isolation gap from the patch edge")
            if params["substrate_h_mm"] + board_ifa_h + params["copper_t_mm"] > params["total_height_limit_mm"]:
                raise ValueError("Board-edge IFA exceeds the total height limit")
            if abs(board_ifa_offset) + board_ifa_w / 2.0 > half_patch - 0.35:
                raise ValueError("Board-edge IFA must stay near the patch edge span")
            if center_radius + half_patch + board_ifa_gap + board_ifa_len > board_radius - 0.20:
                raise ValueError("Board-edge IFA must stay inside the circular board outline")
        if folded_edge_enabled:
            if folded_radial_len <= 0.30 or folded_tangent_len <= 0.50 or folded_w <= 0.06 or folded_w > 0.90:
                raise ValueError("Folded edge arm dimensions must be positive and manufacturable")
            if folded_h <= 0.50:
                raise ValueError("Folded edge arm height must be positive")
            if folded_gap < 0.0:
                raise ValueError("Folded edge arm gap must be non-negative")
            if params["substrate_h_mm"] + folded_h + params["copper_t_mm"] > params["total_height_limit_mm"]:
                raise ValueError("Folded edge arm exceeds the total height limit")
            if abs(folded_offset) + folded_w / 2.0 > half_patch - 0.35:
                raise ValueError("Folded edge arm riser must attach within the patch edge span")
            if abs(folded_offset) + folded_tangent_len + folded_w / 2.0 > half_patch - 0.20:
                raise ValueError("Folded edge arm tangent section must stay inside the board-edge span")
            if center_radius + half_patch + folded_gap + folded_radial_len > board_radius - 0.20:
                raise ValueError("Folded edge arm radial section must stay inside the circular board outline")
        monopole_enabled = params.get("board_edge_fed_monopole_enabled", 0.0) >= 0.5
        fed_ifa_enabled = params.get("board_edge_fed_ifa_enabled", 0.0) >= 0.5
        l_match_enabled = params.get("board_edge_fed_l_match_enabled", 0.0) >= 0.5
        l_match_stub_l = params.get("board_edge_fed_l_match_stub_length_mm", 0.0)
        l_match_stub_w = params.get("board_edge_fed_l_match_stub_width_mm", 0.18)
        l_match_fold_enabled = params.get("board_edge_fed_l_match_fold_enabled", 0.0) >= 0.5
        l_match_fold_l = params.get("board_edge_fed_l_match_fold_length_mm", 0.0)
        l_match_fold_w = params.get("board_edge_fed_l_match_fold_width_mm", l_match_stub_w)
        l_match_fold_radial_sign = 1.0 if params.get("board_edge_fed_l_match_fold_radial_sign", 1.0) >= 0.0 else -1.0
        l_match_cap = params.get("board_edge_fed_l_match_capacitance_pf", 0.0)
        l_match_ind = params.get("board_edge_fed_l_match_inductance_nh", 0.0)
        l_match_res = params.get("board_edge_fed_l_match_resistance_ohm", 0.0)
        l_series_enabled = params.get("board_edge_fed_l_series_match_enabled", 0.0) >= 0.5
        l_series_w = params.get("board_edge_fed_l_series_match_width_mm", 0.14)
        l_series_cap = params.get("board_edge_fed_l_series_match_capacitance_pf", 0.0)
        l_series_ind = params.get("board_edge_fed_l_series_match_inductance_nh", 0.0)
        l_series_res = params.get("board_edge_fed_l_series_match_resistance_ohm", 0.0)
        l_feed_neck_enabled = params.get("board_edge_fed_l_feed_neck_enabled", 0.0) >= 0.5
        l_feed_neck_l = params.get("board_edge_fed_l_feed_neck_length_mm", 0.0)
        l_feed_neck_w = params.get("board_edge_fed_l_feed_neck_width_mm", 0.14)
        if monopole_enabled and fed_ifa_enabled:
            raise ValueError("Use either the board-edge-fed monopole or board-edge-fed IFA in one candidate, not both")
        if l_match_enabled or l_feed_neck_enabled or l_series_enabled:
            if not monopole_enabled and not fed_ifa_enabled:
                raise ValueError("Board-edge-fed L-port matching features require a true low-elevation feed")
        if l_feed_neck_enabled:
            if l_feed_neck_l <= 0.0 or l_feed_neck_w <= 0.04 or l_feed_neck_w > 0.80:
                raise ValueError("Board-edge-fed L-port feed neck dimensions must be manufacturable")
        if l_match_enabled:
            if l_match_stub_l < 0.0 or l_match_stub_w <= 0.04 or l_match_stub_w > 0.80:
                raise ValueError("Board-edge-fed L-port match stub dimensions must be manufacturable")
            if l_match_cap < 0.0 or l_match_ind < 0.0 or l_match_res < 0.0:
                raise ValueError("Board-edge-fed L-port match RLC values must be non-negative")
            if l_match_stub_l <= 1e-9 and l_match_cap <= 0.0 and l_match_ind <= 0.0 and l_match_res <= 0.0:
                raise ValueError("Board-edge-fed L-port match needs a stub or a non-zero RLC value")
        if l_series_enabled:
            if l_feed_neck_l <= 0.0:
                raise ValueError("Board-edge-fed L-port series match requires a positive source-island offset")
            if l_series_w <= 0.04 or l_series_w > 0.80:
                raise ValueError("Board-edge-fed L-port series match width must be manufacturable")
            if l_series_cap < 0.0 or l_series_ind < 0.0 or l_series_res < 0.0:
                raise ValueError("Board-edge-fed L-port series match RLC values must be non-negative")
            if l_series_cap <= 0.0 and l_series_ind <= 0.0 and l_series_res <= 0.0:
                raise ValueError("Board-edge-fed L-port series match needs a non-zero RLC value")
        if l_match_fold_enabled:
            if not l_match_enabled or l_match_stub_l <= 1e-9:
                raise ValueError("Board-edge-fed L-port folded match branch requires a straight match stub anchor")
            if l_match_fold_l <= 0.0 or l_match_fold_w <= 0.04 or l_match_fold_w > 0.80:
                raise ValueError("Board-edge-fed L-port folded match branch dimensions must be manufacturable")
        if monopole_enabled:
            mono_h = params.get("board_edge_fed_monopole_height_mm", 4.8)
            mono_w = params.get("board_edge_fed_monopole_width_mm", 0.24)
            mono_gap = params.get("board_edge_fed_monopole_gap_mm", 0.80)
            mono_offset = params.get("board_edge_fed_monopole_offset_mm", 0.0)
            mono_topload = params.get("board_edge_fed_monopole_topload_length_mm", 0.0)
            if mono_h <= 0.50 or mono_w <= 0.06 or mono_w > 0.90 or mono_gap < 0.15 or mono_topload < 0.0:
                raise ValueError("Board-edge-fed monopole dimensions must be positive and manufacturable")
            if params["substrate_h_mm"] + mono_h + params["copper_t_mm"] > params["total_height_limit_mm"]:
                raise ValueError("Board-edge-fed monopole exceeds the total height limit")
            if abs(mono_offset) + mono_w / 2.0 + mono_topload > half_patch - 0.20:
                raise ValueError("Board-edge-fed monopole top loading must stay near the element-side span")
            if center_radius + half_patch + mono_gap > board_radius - 0.25:
                raise ValueError("Board-edge-fed monopole feed point must stay inside the circular board outline")
            l_feature_span = (l_match_stub_l if l_match_enabled else 0.0) + (l_feed_neck_l if (l_feed_neck_enabled or l_series_enabled) else 0.0)
            if (l_match_enabled or l_feed_neck_enabled or l_series_enabled) and abs(mono_offset) + mono_w / 2.0 + l_feature_span > half_patch - 0.20:
                raise ValueError("Board-edge-fed monopole L-port feed neck and match stub must stay near the element-side span")
            if l_match_fold_enabled:
                if l_match_fold_radial_sign >= 0.0 and center_radius + half_patch + mono_gap + l_match_fold_l > board_radius - 0.20:
                    raise ValueError("Board-edge-fed monopole folded L-port match branch must stay inside the circular board outline")
                if l_match_fold_radial_sign < 0.0 and mono_gap - l_match_fold_l < 0.15:
                    raise ValueError("Board-edge-fed monopole inward folded L-port match branch must stay outside the patch edge")
        if fed_ifa_enabled:
            fed_ifa_l = params.get("board_edge_fed_ifa_length_mm", 3.8)
            fed_ifa_h = params.get("board_edge_fed_ifa_height_mm", 5.2)
            fed_ifa_w = params.get("board_edge_fed_ifa_width_mm", 0.24)
            fed_ifa_gap = params.get("board_edge_fed_ifa_gap_mm", 0.60)
            fed_ifa_feed = params.get("board_edge_fed_ifa_feed_offset_mm", 0.70)
            fed_ifa_offset = params.get("board_edge_fed_ifa_offset_mm", 0.0)
            if fed_ifa_l <= 0.80 or fed_ifa_h <= 0.50 or fed_ifa_w <= 0.06 or fed_ifa_w > 0.90 or fed_ifa_gap < 0.15:
                raise ValueError("Board-edge-fed IFA dimensions must be positive and manufacturable")
            if fed_ifa_feed <= 0.10 or fed_ifa_feed >= fed_ifa_l - 0.10:
                raise ValueError("Board-edge-fed IFA feed tap must sit between the short and open end")
            if params["substrate_h_mm"] + fed_ifa_h + params["copper_t_mm"] > params["total_height_limit_mm"]:
                raise ValueError("Board-edge-fed IFA exceeds the total height limit")
            if abs(fed_ifa_offset) + fed_ifa_w / 2.0 > half_patch - 0.20:
                raise ValueError("Board-edge-fed IFA must stay near the element-side span")
            if center_radius + half_patch + fed_ifa_gap + fed_ifa_l > board_radius - 0.20:
                raise ValueError("Board-edge-fed IFA must stay inside the circular board outline")
            l_feature_span = (l_match_stub_l if l_match_enabled else 0.0) + (l_feed_neck_l if (l_feed_neck_enabled or l_series_enabled) else 0.0)
            if (l_match_enabled or l_feed_neck_enabled or l_series_enabled) and abs(fed_ifa_offset) + fed_ifa_w / 2.0 + l_feature_span > half_patch - 0.20:
                raise ValueError("Board-edge-fed IFA L-port feed neck and match stub must stay near the element-side span")
            if l_match_fold_enabled:
                if l_match_fold_radial_sign >= 0.0 and center_radius + half_patch + fed_ifa_gap + fed_ifa_feed + l_match_fold_l > board_radius - 0.20:
                    raise ValueError("Board-edge-fed IFA folded L-port match branch must stay inside the circular board outline")
                if l_match_fold_radial_sign < 0.0 and fed_ifa_gap + fed_ifa_feed - l_match_fold_l < 0.15:
                    raise ValueError("Board-edge-fed IFA inward folded L-port match branch must stay outside the patch edge")
        if ab_cancel_enabled:
            if ab_cancel_l <= 0.40 or ab_cancel_w <= 0.03 or ab_cancel_w > 0.30:
                raise ValueError("Dual-polarized A/B cancellation trace dimensions must be manufacturable")
            if ab_cancel_gap < 0.04 or ab_cancel_gap > 0.40:
                raise ValueError("Dual-polarized A/B cancellation coupling gap must be between 0.04 and 0.40 mm")
            if ab_cancel_z_offset < -0.02 or ab_cancel_z_offset >= feed_h - 0.04:
                raise ValueError("Dual-polarized A/B cancellation network z offset must stay inside the feed dielectric")
            coupling_edge = feed_w / 2.0 + ab_cancel_gap + ab_cancel_w / 2.0
            if ab_cancel_phase_offset - ab_cancel_l / 2.0 <= coupling_edge + 0.05:
                raise ValueError("Dual-polarized A/B cancellation network needs a positive phase-line span")
            if ab_cancel_phase_offset + ab_cancel_l / 2.0 > half_patch - 0.35:
                raise ValueError("Dual-polarized A/B cancellation network must stay below the patch footprint")
        if stub_enabled and (stub_len <= 0.0 or stub_w <= 0.0 or stub_offset <= 0.0 or stub_offset >= feed_len / 2.0 - 0.15):
            raise ValueError("Dual-polarized slot-coupled tuning stub dimensions must be positive and stay on the feedline")
        if stub2_enabled and (stub2_len <= 0.0 or stub2_w <= 0.0 or stub2_offset <= 0.0 or stub2_offset >= feed_len / 2.0 - 0.15):
            raise ValueError("Dual-polarized slot-coupled second tuning stub dimensions must be positive and stay on the feedline")
        if step_enabled and (step_len <= 0.0 or step_w <= feed_w or step_len >= feed_len / 2.0 - 0.15):
            raise ValueError("Dual-polarized slot-coupled feed step must be wider than the feedline and stay near the port")
        aperture_extent = max(
            abs(aperture_a_u) + aperture_w / 2.0,
            abs(aperture_a_v) + aperture_len_a / 2.0,
            abs(aperture_b_u) + aperture_len_b / 2.0,
            abs(aperture_b_v) + aperture_w / 2.0,
        )
        if aperture_extent > half_patch - 0.25:
            raise ValueError("Dual-polarized slot apertures must stay below the patch aperture")
        feedline_extent = feed_len / 2.0 + max(abs(feedline_a_v), abs(feedline_b_u)) + feed_w
        if stub_enabled:
            stub_extent = max(
                abs(stub_offset) + stub_w / 2.0,
                max(abs(feedline_a_v), abs(feedline_b_u)) + feed_w / 2.0 + stub_len,
            )
            feedline_extent = max(feedline_extent, stub_extent)
        if stub2_enabled:
            stub2_extent = max(
                abs(stub2_offset) + stub2_w / 2.0,
                max(abs(feedline_a_v), abs(feedline_b_u)) + feed_w / 2.0 + stub2_len,
            )
            feedline_extent = max(feedline_extent, stub2_extent)
        if step_enabled:
            step_extent = feed_len / 2.0 + max(abs(feedline_a_v), abs(feedline_b_u)) + step_w
            feedline_extent = max(feedline_extent, step_extent)
        if a_res_len > 1e-9 or a_res_w > 1e-9:
            feedline_extent = max(feedline_extent, max(a_res_len, a_res_w) / 2.0 + max(abs(feedline_a_v), abs(feedline_b_u)))
        if ab_cancel_enabled:
            feedline_extent = max(feedline_extent, ab_cancel_phase_offset + ab_cancel_l / 2.0 + ab_cancel_w)
        if center_radius + feedline_extent > board_radius - 0.25:
            raise ValueError("Dual-polarized underside feedline too close to board edge")
    if params.get("weak_coupling_open_line_enabled", 0.0) >= 0.5:
        line_len = params.get("weak_coupling_open_line_length_mm", 0.0)
        line_w = params.get("weak_coupling_open_line_width_mm", 0.0)
        line_offset = params.get("weak_coupling_open_line_offset_mm", params["feed_offset_u_mm"] / 2.0)
        if line_len <= 0.0 or line_w <= 0.0:
            raise ValueError("Weak coupling open line length and width must be positive")
        half_extent = (line_len + line_w) / (2.0 * math.sqrt(2.0))
        half_patch = params["patch_side_mm"] / 2.0
        if line_offset - half_extent < -half_patch + 0.20 or line_offset + half_extent > half_patch - 0.20:
            raise ValueError("Weak coupling open line must stay above the patch interior")
    if params.get("via_fence_enabled", 0.0) >= 0.5:
        radius = params.get("via_fence_radius_mm", 0.0)
        count = max(1, int(round(params.get("via_fence_count", 1.0))))
        pitch = params.get("via_fence_pitch_mm", 0.0)
        edge_offset = params.get("via_fence_edge_offset_mm", 0.0)
        center_pos = params.get("via_fence_center_mm", params["feed_offset_u_mm"])
        if radius <= 0.0 or pitch <= 0.0 or edge_offset <= radius:
            raise ValueError("Via fence radius, pitch, and edge offset must be positive")
        max_leg_pos = center_pos + (count - 1) * pitch / 2.0 + radius
        edge = params["patch_side_mm"] / 2.0
        fence_corner = math.hypot(edge + edge_offset + radius, min(max_leg_pos, edge) + radius)
        if center_radius + fence_corner > board_radius - 0.15:
            raise ValueError("Via fence too close to board edge")
    if params.get("microstrip_feed_enabled", 0.0) >= 0.5:
        line_len = params.get("microstrip_feedline_length_mm", 0.0)
        if line_len <= 0.15:
            raise ValueError("Microstrip feedline length must be positive")
        network_corner = params["patch_side_mm"] / 2.0 + max(
            line_len,
            params.get("neutralization_branch_length_mm", 0.0),
            params.get("neutralization_branch_offset_mm", 0.0),
            params.get("microstrip_match_length_mm", 0.0) + params.get("microstrip_transform2_length_mm", 0.0),
            params.get("microstrip_stub_offset_mm", 0.0) + params.get("microstrip_stub_length_mm", 0.0),
            abs(params.get("microstrip_feed_offset_mm", 0.0)) + params.get("microstrip_feedline_width_mm", 0.0) / 2.0,
        )
        if center_radius + math.sqrt(2.0) * network_corner > board_radius - 0.2:
            raise ValueError("Microstrip matching network too close to board edge")


def clean_outputs(paths: dict[str, Path]) -> None:
    for log_path in paths["project"].parent.glob(f"{paths['project'].stem}*_batchsolve.log"):
        try:
            log_path.unlink()
        except OSError:
            pass
    for log_path in paths["project"].parent.glob(f"{paths['project'].stem}*_pyaedt_solve.log"):
        try:
            log_path.unlink()
        except OSError:
            pass
    for path in [
        paths["results"],
        paths["pyaedt"],
        paths["project"].with_suffix(".aedt.lock"),
        paths["project"].with_suffix(".aedt.auto"),
        paths["project"].with_suffix(".previous.aedt"),
        paths["project"].with_suffix(".batchsolve.log"),
    ]:
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


def save_project_best_effort(hfss: Hfss, stage: str) -> None:
    try:
        hfss.save_project()
    except Exception as exc:
        print(f"Project save skipped after {stage}: {exc}", flush=True)


def latest_hfss_profile_status(results_path: Path) -> tuple[str | None, str]:
    profiles = sorted(results_path.rglob("*.profile"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not profiles:
        return None, ""
    profile = profiles[0]
    try:
        text = profile.read_text(errors="ignore")
    except OSError:
        return None, str(profile)
    if "Status\\', \\'Normal Completion" in text or "Status', 'Normal Completion" in text:
        return "normal", str(profile)
    if "Status\\', \\'Failed" in text or "Status', 'Failed" in text:
        return "failed", str(profile)
    return None, str(profile)


def wait_for_hfss_profile_completion(results_path: Path, timeout_s: float = 3600.0, poll_s: float = 10.0) -> bool:
    deadline = time.time() + timeout_s
    last_profile = ""
    while time.time() < deadline:
        status, profile = latest_hfss_profile_status(results_path)
        last_profile = profile or last_profile
        if status == "normal":
            print(f"Stage: HFSS profile normal completion detected in {Path(profile).name}", flush=True)
            return True
        if status == "failed":
            print(f"Stage: HFSS profile failure detected in {Path(profile).name}", flush=True)
            return False
        time.sleep(poll_s)
    print(f"Stage: HFSS profile wait timed out; last profile={last_profile or 'none'}", flush=True)
    return False


def batch_solve_project(project: Path, design: str, setup_name: str, results_path: Path, timeout_s: float = 3600.0) -> bool:
    targets = [f"{design}:Nominal:{setup_name}", f"{design}:Nominal", ""]
    for target in targets:
        log_suffix = "all" if not target else target.replace(":", "_")
        log_path = project.with_name(f"{project.stem}_{log_suffix}_batchsolve.log")
        cmd = [str(AEDT_EXE), "-ng", "-LogFile", str(log_path), "-BatchSolve"]
        if target:
            cmd.append(target)
        cmd.append(str(project))
        print(f"Stage: AEDT batch solve command: {' '.join(cmd)}", flush=True)
        completed_returncode: int | None = None
        try:
            process = subprocess.Popen(cmd, cwd=str(ROOT))
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                completed_returncode = process.poll()
                status, profile = latest_hfss_profile_status(results_path)
                if status == "normal":
                    print(f"Stage: HFSS profile normal completion detected in {Path(profile).name}", flush=True)
                    print("Stage: AEDT batch solve profile completed; terminating batch process", flush=True)
                    process.terminate()
                    try:
                        process.wait(timeout=30.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=30.0)
                    return True
                if status == "failed":
                    print(f"Stage: HFSS profile failure detected in {Path(profile).name}", flush=True)
                    process.terminate()
                    process.wait(timeout=30.0)
                    break
                if completed_returncode is not None:
                    break
                time.sleep(2.0)
            if completed_returncode is None:
                process.kill()
                process.wait(timeout=30.0)
                print(f"Stage: AEDT batch solve timed out for target {target or 'all'}", flush=True)
                continue
        except subprocess.TimeoutExpired:
            print(f"Stage: AEDT batch solve timed out for target {target or 'all'}", flush=True)
            continue
        print(f"Stage: AEDT batch solve exit code {completed_returncode}", flush=True)
        if wait_for_hfss_profile_completion(results_path, timeout_s=30.0, poll_s=2.0):
            return True
    return False


def terminate_process_tree(pid: int) -> None:
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def remove_project_lock(project: Path) -> None:
    for lock_path in [project.with_suffix(".aedt.lock"), project.with_suffix(".lock")]:
        try:
            lock_path.unlink()
        except OSError:
            pass


def pyaedt_solve_project(
    project: Path,
    design: str,
    setup_name: str,
    results_path: Path,
    cores: int,
    tasks: int,
    timeout_s: float = 3600.0,
    startup_timeout_s: float = 180.0,
) -> bool:
    log_path = project.with_name(f"{project.stem}_{design}_{setup_name}_pyaedt_solve.log")
    remove_project_lock(project)
    cmd = [
        sys.executable,
        str(PYAEDT_SOLVE_HELPER),
        "--project",
        str(project),
        "--design",
        design,
        "--setup",
        setup_name,
        "--cores",
        str(cores),
        "--tasks",
        str(tasks),
    ]
    print(f"Stage: PyAEDT solve helper command: {' '.join(cmd)}", flush=True)
    with log_path.open("w", encoding="utf-8", errors="ignore") as log_file:
        process = subprocess.Popen(cmd, cwd=str(ROOT), stdout=log_file, stderr=subprocess.STDOUT)
        deadline = time.time() + timeout_s
        startup_deadline = time.time() + startup_timeout_s
        helper_opened = False
        while time.time() < deadline:
            status, profile = latest_hfss_profile_status(results_path)
            if status == "normal":
                print(f"Stage: HFSS profile normal completion detected in {Path(profile).name}", flush=True)
                time.sleep(5.0)
                terminate_process_tree(process.pid)
                return True
            if status == "failed":
                print(f"Stage: HFSS profile failure detected in {Path(profile).name}", flush=True)
                terminate_process_tree(process.pid)
                return False
            if process.poll() is not None:
                break
            if not helper_opened:
                try:
                    helper_log = log_path.read_text(encoding="utf-8", errors="ignore")
                    helper_opened = "Stage: helper project opened" in helper_log or "Stage: helper solving" in helper_log
                except OSError:
                    helper_log = ""
                if time.time() >= startup_deadline and not helper_opened and status is None:
                    print("Stage: PyAEDT solve helper startup timed out before project open", flush=True)
                    terminate_process_tree(process.pid)
                    return False
            time.sleep(5.0)
        returncode = process.poll()
        if returncode is None:
            print("Stage: PyAEDT solve helper timed out", flush=True)
            terminate_process_tree(process.pid)
            return False
        print(f"Stage: PyAEDT solve helper exit code {returncode}", flush=True)
    return wait_for_hfss_profile_completion(results_path, timeout_s=30.0, poll_s=2.0)


def reopen_hfss_project(paths: dict[str, Path], design: str, non_graphical: bool) -> Hfss:
    remove_project_lock(paths["project"])
    print(f"Stage: reopening solved project for postprocess: {paths['project']}", flush=True)
    hfss = Hfss(
        project=str(paths["project"]),
        design=design,
        solution_type="DrivenModal",
        version="2023.1",
        non_graphical=non_graphical,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    hfss.design_solutions._solution_type = SolutionsHfss.DrivenModal
    print(f"Stage: solved project reopened for postprocess: {design}", flush=True)
    return hfss


def build_project(
    topology: str,
    analyze: bool = False,
    non_graphical: bool = False,
    quick: bool = False,
    band_samples: bool = False,
    sparam_only: bool = False,
    return_hfss: bool = False,
    analysis_cores: int | None = None,
    analysis_tasks: int | None = None,
):
    patch_pyaedt_empty_variable_lists()
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
    hfss.design_solutions._solution_type = SolutionsHfss.DrivenModal

    substrate_material = add_ro4350b(hfss, params)
    board_radius = params["board_diameter_mm"] / 2.0
    h = params["substrate_h_mm"]
    center_radius = params["element_spacing_mm"] / math.sqrt(2.0)
    substrate = hfss.modeler.create_cylinder("Z", [0, 0, 0], board_radius, h, num_sides=128, name=f"{spec['label']}_substrate", material=substrate_material)
    print("Stage: substrate created", flush=True)
    substrate.transparency = 0.65
    if has_dualpol_slotcoupled(params):
        feed_h = params.get("feed_substrate_h_mm", 0.254)
        feed_substrate_h = feed_h + max(
            params.get("slot_coupled_b_feed_layer_offset_mm", 0.0),
            params.get("slot_coupled_bridge_offset_mm", 0.0) if params.get("slot_coupled_bridge_enabled", 0.0) >= 0.5 else 0.0,
        )
        feed_substrate = hfss.modeler.create_cylinder(
            "Z",
            [0, 0, -feed_substrate_h],
            board_radius,
            feed_substrate_h,
            num_sides=128,
            name=f"{spec['label']}_feed_substrate",
            material=substrate_material,
        )
        feed_substrate.transparency = 0.72
        print("Stage: feed substrate created", flush=True)
    ground = hfss.modeler.create_circle("XY", [0, 0, 0], params["ground_radius_mm"], num_sides=128, name=f"{spec['label']}_bottom_ground", material="copper")
    print("Stage: ground created", flush=True)
    metal_names = [ground.name]
    slot_names = add_isolation_slot_sheets(hfss, params)
    slot_names.extend(add_local_dgs_slots(hfss, params))
    print("Stage: substrate, ground, and isolation slots created", flush=True)

    kind = spec["kind"]
    for tag, angle in ELEMENTS:
        print(f"Stage: creating element {tag}", flush=True)
        cx = center_radius * math.cos(math.radians(angle))
        cy = center_radius * math.sin(math.radians(angle))
        if kind == "dualfeed":
            metal_names.extend(add_dualfeed_element(hfss, tag, (cx, cy), angle, params))
        elif kind == "hybrid":
            metal_names.extend(add_dualfeed_element(hfss, tag, (cx, cy), angle, params, hybrid_traces=True))
        elif kind == "dualpol":
            if has_dualpol_slotcoupled(params):
                metals, slots = add_dualpol_slotcoupled_element(hfss, tag, (cx, cy), 0.0, params)
                metal_names.extend(metals)
                slot_names.extend(slots)
                metal_names.extend(add_board_edge_fed_low_elevation_unit(hfss, tag, (cx, cy), 0.0, params))
            else:
                metal_names.extend(add_dualfeed_element(hfss, tag, (cx, cy), 0.0, params))
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

    total_height = params["substrate_h_mm"] + 2.0 * params["copper_t_mm"]
    if has_stacked_parasitic(params):
        total_height += params.get("air_gap_mm", 0.0)
        total_height += params["copper_t_mm"]
    if has_dualpol_slotcoupled(params):
        total_height += params.get("feed_substrate_h_mm", 0.254) + params["copper_t_mm"]
    if params.get("weak_coupling_open_line_enabled", 0.0) >= 0.5:
        total_height = max(
            total_height,
            params["substrate_h_mm"] + params.get("weak_coupling_open_line_gap_mm", 0.08) + params["copper_t_mm"],
        )
    if params.get("slot_coupled_edge_wall_enabled", 0.0) >= 0.5:
        total_height = max(
            total_height,
            params["substrate_h_mm"] + params.get("slot_coupled_edge_wall_height_mm", 2.0) + params["copper_t_mm"],
        )
    if params.get("slot_coupled_board_edge_ifa_enabled", 0.0) >= 0.5:
        total_height = max(
            total_height,
            params["substrate_h_mm"] + params.get("slot_coupled_board_edge_ifa_height_mm", 3.8) + params["copper_t_mm"],
        )
    if params.get("slot_coupled_folded_edge_arm_enabled", 0.0) >= 0.5:
        total_height = max(
            total_height,
            params["substrate_h_mm"] + params.get("slot_coupled_folded_edge_arm_height_mm", 5.2) + params["copper_t_mm"],
        )
    if params.get("board_edge_fed_monopole_enabled", 0.0) >= 0.5:
        total_height = max(
            total_height,
            params["substrate_h_mm"] + params.get("board_edge_fed_monopole_height_mm", 4.8) + params["copper_t_mm"],
        )
    if params.get("board_edge_fed_ifa_enabled", 0.0) >= 0.5:
        total_height = max(
            total_height,
            params["substrate_h_mm"] + params.get("board_edge_fed_ifa_height_mm", 5.2) + params["copper_t_mm"],
        )
    notes = {
        "project": str(paths["project"]),
        "design": hfss.design_name,
        "topology": topology,
        "label": spec["label"],
        "model": spec["description"],
        "pcb_constraint": "Circular PCB, diameter 44 mm.",
        "height_constraint": f"PCB + copper/topology height {total_height:.3f} mm <= {params['total_height_limit_mm']} mm.",
        "cp_target": "Dual-polarized topology treats axial ratio as a derived digital-combining reference, not the primary target." if topology == "dualpol" else "AxialRatioValue <= 3 dB in the selected FOV and CH9 frequencies.",
        "fov_target": "HFSS spherical coordinates: Theta 45-90 deg and Phi 0-360 deg, GainTotal min >= -5 dBi.",
        "source_guidance": source_guidance(topology),
        "parameters": params,
    }
    paths["params"].write_text(json.dumps(notes, indent=2), encoding="utf-8")

    save_project_best_effort(hfss, "setup creation")
    if analyze:
        print(f"Stage: {spec['label']} analysis started", flush=True)
        hfss.release_desktop(close_projects=True, close_desktop=non_graphical)
        time.sleep(15.0)
        remove_project_lock(paths["project"])
        cores = int(analysis_cores or params.get("analysis_cores", 8))
        tasks = int(analysis_tasks or params.get("analysis_tasks", cores))
        ok = pyaedt_solve_project(paths["project"], spec["design"], setup.name, paths["results"], cores, tasks)
        if not ok:
            ok = batch_solve_project(paths["project"], spec["design"], setup.name, paths["results"])
        print(f"Analyze result: {ok}", flush=True)
        time.sleep(10.0)
        remove_project_lock(paths["project"])
        if return_hfss:
            hfss = reopen_hfss_project(paths, spec["design"], non_graphical)
        else:
            return paths["project"]
    if return_hfss:
        return paths["project"], hfss
    hfss.release_desktop(close_projects=False, close_desktop=non_graphical)
    return paths["project"]


def source_guidance(topology: str) -> list[str]:
    if topology == "dualpol":
        guidance = [
            "A feeds are aligned to the global X-polarized channel and B feeds are aligned to the global Y-polarized channel.",
            "Do not apply a fixed 90 degree hybrid for signoff; use independent X/Y receiver channels or digital polarization combining.",
            "Evaluate linear incident polarizations 0/45/90/135 deg and use vector calibration to reduce PDOA curve drift.",
        ]
        params = topology_params(topology)
        if params.get("microstrip_feed_enabled", 0.0) >= 0.5:
            guidance.append("The dual-polarized feed uses equal-length edge microstrip transitions with tunable matching sections.")
        if params.get("microstrip_feed_mirror_enabled", 0.0) >= 0.5:
            guidance.append("The edge feedlines are mirrored by element position to improve array pattern symmetry.")
        if params.get("neutralization_branch_enabled", 0.0) >= 0.5:
            guidance.append("Same-element X/Y neutralization branches are enabled and should be co-tuned with receiver calibration.")
        if params.get("dualpol_parasitic_enabled", 0.0) >= 0.5:
            guidance.append("A stacked parasitic patch is enabled above each dual-polarized driven patch to decouple feed layout from the radiating aperture.")
        if params.get("dualpol_slotcoupled_enabled", 0.0) >= 0.5:
            guidance.append("A/B ports use underside microstrip feedlines coupled through orthogonal ground apertures; tune aperture windows and feed substrate thickness together.")
        if params.get("slot_coupled_board_edge_ifa_enabled", 0.0) >= 0.5:
            guidance.append("A parasitic board-edge IFA is enabled to add a dedicated low-elevation current path near the PCB rim.")
        if params.get("slot_coupled_folded_edge_arm_enabled", 0.0) >= 0.5:
            guidance.append("A raised folded edge arm is enabled; the candidate intentionally spends height to improve horizontal-plane coverage.")
        if params.get("board_edge_fed_monopole_enabled", 0.0) >= 0.5:
            guidance.append("Independent board-edge-fed monopole ports P1L-P4L are enabled as selectable low-elevation coverage elements.")
        if params.get("board_edge_fed_ifa_enabled", 0.0) >= 0.5:
            guidance.append("Independent board-edge-fed IFA ports P1L-P4L are enabled as selectable low-elevation coverage elements.")
        if params.get("board_edge_fed_l_match_enabled", 0.0) >= 0.5:
            guidance.append("A dedicated shunt matching stub is enabled on each low-elevation L port and must be co-optimized with coverage loss.")
        if params.get("board_edge_fed_l_series_match_enabled", 0.0) >= 0.5:
            guidance.append("A dedicated series lumped RLC element is enabled between the low-elevation L-port source island and the board-edge radiator.")
        if params.get("board_edge_fed_l_match_fold_enabled", 0.0) >= 0.5:
            guidance.append("The low-elevation L-port matching stub uses a folded open branch to add electrical length without consuming more board-edge span.")
        if params.get("board_edge_fed_l_feed_neck_enabled", 0.0) >= 0.5:
            guidance.append("A series feed neck moves each low-elevation L-port feed point along the board edge before the monopole/IFA attachment.")
        if params.get("rf_switch_equiv_enabled", 0.0) >= 0.5:
            guidance.append("RF-switch working-state modeling is enabled: the selected polarization remains a lumped port and the inactive polarization is replaced by a parallel off-state R/C/L load.")
        return guidance
    if topology in {"dualfeed", "hybrid"}:
        guidance = [
            "A/B feeds on each patch are intended for 90 degree quadrature excitation.",
            "Use per-element quadrature source cases for CP checks.",
        ]
        params = topology_params(topology)
        if params.get("microstrip_feed_enabled", 0.0) >= 0.5:
            guidance.append("The feed is upgraded to edge microstrip matching sections with optional A/B neutralization and local DGS tuning.")
        if params.get("weak_coupling_open_line_enabled", 0.0) >= 0.5:
            guidance.append("A floating A/B weak-coupling open line is enabled above each patch for isolation tuning.")
        if params.get("via_fence_enabled", 0.0) >= 0.5:
            guidance.append("Grounded via fences are enabled outside the A/B feed quadrant of each patch.")
        elif topology == "hybrid":
            guidance.append("The hybrid topology includes printable branch trace placeholders; final layout needs a controlled-impedance network extraction.")
        return guidance
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
    parser.add_argument("--cores", type=int, default=None, help="HFSS analysis cores")
    parser.add_argument("--tasks", type=int, default=None, help="HFSS analysis tasks")
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
        analysis_cores=args.cores,
        analysis_tasks=args.tasks,
    )
    print(path)


if __name__ == "__main__":
    main()

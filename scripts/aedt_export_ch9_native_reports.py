import os
import sys
import time

AEDT_PLUGIN = r"D:\Program Files\AnsysEM\v231\Win64\PythonFiles\DesktopPlugin"
if AEDT_PLUGIN not in sys.path:
    sys.path.append(AEDT_PLUGIN)

import ScriptEnv


ROOT = os.path.abspath(os.getcwd())
PROJECT_PATH = os.environ.get(
    "D44_AEDT_PROJECT",
    os.path.join(ROOT, "UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt"),
)
PROJECT_NAME = os.environ.get("D44_AEDT_PROJECT_NAME", "UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY")
DESIGN_NAME = os.environ.get("D44_AEDT_DESIGN", "Array4_Diamond_D44_DualPolarized_XY")
SOLUTION = os.environ.get("D44_AEDT_SOLUTION", "Setup_CH9 : Sweep_CH9")
SPHERE = os.environ.get("D44_AEDT_SPHERE", "Upper_Hemisphere_5deg")
OUT_DIR = os.environ.get(
    "D44_AEDT_OUT_DIR",
    os.path.join(ROOT, "reports_d44_dualpol_truefed_l_fov_gain_check"),
)
CASE_NAME = os.environ.get("D44_AEDT_CASE", "case")
FREQ_GHZ = os.environ.get("D44_AEDT_FREQ_GHZ", "8")


def safe_name(value):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    tag = safe_name(CASE_NAME) + "_" + str(int(time.time()))
    s_csv = os.path.join(OUT_DIR, safe_name(CASE_NAME) + "_native_s_parameters.csv")
    ff_csv = os.path.join(OUT_DIR, safe_name(CASE_NAME) + "_native_farfield_default.csv")
    sources_txt = os.path.join(OUT_DIR, safe_name(CASE_NAME) + "_native_sources.txt")

    ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
    oDesktop.RestoreWindow()
    oDesktop.OpenProject(PROJECT_PATH)
    oProject = oDesktop.SetActiveProject(PROJECT_NAME)
    oDesign = oProject.SetActiveDesign(DESIGN_NAME)
    oReport = oDesign.GetModule("ReportSetup")
    oSolutions = oDesign.GetModule("Solutions")
    sources = list(oSolutions.GetAllSources())
    with open(sources_txt, "w") as f:
        for source in sources:
            f.write(str(source) + "\n")

    s_expressions = ["dB(S({0},{0}))".format(source) for source in sources]
    active_sources = [source for source in sources if str(source).endswith("A") or str(source).endswith("B")]
    for left in active_sources:
        for right in active_sources:
            if left != right:
                s_expressions.append("dB(S({0},{1}))".format(left, right))

    s_report = "D44_S_" + tag
    oReport.CreateReport(
        s_report,
        "Modal Solution Data",
        "Data Table",
        SOLUTION,
        [],
        ["Freq:=", ["All"]],
        ["X Component:=", "Freq", "Y Component:=", s_expressions],
        [],
    )
    oReport.ExportToFile(s_report, s_csv, False)

    ff_report = "D44_FF_" + tag
    oReport.CreateReport(
        ff_report,
        "Far Fields",
        "Rectangular Plot",
        SOLUTION,
        ["Context:=", SPHERE],
        ["Freq:=", [FREQ_GHZ + "GHz"], "Theta:=", ["All"], "Phi:=", ["All"]],
        ["X Component:=", "Theta", "Y Component:=", ["dB(GainTotal)", "dB(RealizedGainTotal)"]],
        [],
    )
    oReport.ExportToFile(ff_report, ff_csv, False)
    oDesktop.CloseProject(PROJECT_NAME)
    oDesktop.QuitApplication()


main()

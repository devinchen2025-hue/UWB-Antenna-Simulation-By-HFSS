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
    os.path.join(ROOT, "reports_d44_dualpol_truefed_l_polarization_phase"),
)
CASE_NAME = os.environ.get("D44_AEDT_CASE", "case")
FREQ_GHZ = os.environ.get("D44_AEDT_FREQ_GHZ", "8")


def safe_name(value):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    tag = safe_name(CASE_NAME) + "_" + str(int(time.time()))
    fields_csv = os.path.join(OUT_DIR, safe_name(CASE_NAME) + "_native_field_components.csv")
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

    report = "D44_FIELD_" + tag
    oReport.CreateReport(
        report,
        "Far Fields",
        "Rectangular Plot",
        SOLUTION,
        ["Context:=", SPHERE],
        ["Freq:=", [FREQ_GHZ + "GHz"], "Theta:=", ["All"], "Phi:=", ["All"]],
        [
            "X Component:=",
            "Phi",
            "Y Component:=",
            ["re(rETheta)", "im(rETheta)", "re(rEPhi)", "im(rEPhi)"],
        ],
        [],
    )
    oReport.ExportToFile(report, fields_csv, False)
    oDesktop.CloseProject(PROJECT_NAME)
    oDesktop.QuitApplication()


main()

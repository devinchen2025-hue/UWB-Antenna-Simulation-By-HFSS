from __future__ import annotations

import argparse
from pathlib import Path

from ansys.aedt.core import Hfss
from ansys.aedt.core.generic.constants import SolutionsHfss

import build_uwb_ch9_hfss_d44_topology as builder


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve an existing D44 HFSS setup in an isolated PyAEDT process.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--setup", required=True)
    parser.add_argument("--cores", type=int, default=1)
    parser.add_argument("--tasks", type=int, default=1)
    args = parser.parse_args()

    builder.patch_pyaedt_empty_variable_lists()
    project_path = Path(args.project)
    builder.remove_project_lock(project_path)
    print(f"Stage: helper opening {project_path}", flush=True)
    hfss = Hfss(
        project=str(project_path),
        design=args.design,
        solution_type="DrivenModal",
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    print(f"Stage: helper project opened {args.design}", flush=True)
    hfss.design_solutions._solution_type = SolutionsHfss.DrivenModal
    print(f"Stage: helper solving {args.design}:{args.setup}", flush=True)
    hfss.analyze_setup(args.setup, cores=args.cores, tasks=args.tasks, blocking=True)
    print("Stage: helper analyze returned", flush=True)


if __name__ == "__main__":
    main()

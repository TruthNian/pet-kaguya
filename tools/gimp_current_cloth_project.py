"""Versioned GIMP batch entry for the current cloth; never overwrite v1."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'tools/gimp_sleeve_project.py'),run_name='__main__',init_globals={
    'MATERIAL_INPUT':ROOT/'candidates/phase5/review-sleeves-v2',
    'PARENT_COMPOSITION':'review-art-v5',
    'PROJECT_OUTPUT':ROOT/'sources/editor/review-sleeves-v2'})

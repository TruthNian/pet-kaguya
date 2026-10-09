"""Fresh, actual GIMP batch project for the complete raised waiting garment."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'tools/gimp_sleeve_project.py'),run_name='__main__',init_globals={
    'MATERIAL_INPUT':ROOT/'candidates/phase5/waiting-sleeve-v1',
    'MATERIAL_NAME':'mapped-material.png','PARENT_COMPOSITION':'waiting-art-v1',
    'PROJECT_NAME':'kaguya-waiting-sleeve.xcf',
    'BASE_LABEL':'01 Locked waiting v1 - original held hand, face, cape and torso',
    'MATERIAL_LABEL':'02 Raised garment and bounded backing - editable compensated mask',
    'PROJECT_OUTPUT':ROOT/'sources/editor/waiting-sleeve'})

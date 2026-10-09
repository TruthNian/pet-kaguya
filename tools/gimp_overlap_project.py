"""Save/reopen a real static overlap study, not an approved animation layer."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'tools/gimp_sleeve_project.py'),run_name='__main__',init_globals={
    'MATERIAL_INPUT':ROOT/'candidates/phase5/review-hands-overlap-v1',
    'MATERIAL_NAME':'mapped-material.png','PARENT_COMPOSITION':'review-art-v6',
    'PROJECT_NAME':'kaguya-review-overlap.xcf',
    'BASE_LABEL':'01 Locked review v6 - original body alpha, face, hair and costume',
    'MATERIAL_LABEL':'02 Low relaxed overlapping hands - RGB repaint on parent alpha',
    'PROJECT_OUTPUT':ROOT/'sources/editor/review-overlap'})

"""Where everything lives, for the OMF3K tools.

    omf3k/prototype   C sources of the 3D viewer, with the tables generated for it next to them
    omf3k/tools       Python tools (this folder)
    omf3k/data        hand-kept catalogs: pose_catalog.csv, pose_sprite_groups.csv, move_names.csv
    omf3k/web         page templates for the generated HTML tools
    omf3k/scripts     PowerShell launchers
    omf3k/docs        documentation
    omf3k/build       everything the tools generate (ignored by git)
    build/            OpenOMF's own CMake and vcpkg trees, with the exes and the recorded traces

Tools get their locations from here instead of computing them, so a folder can move in one place.
"""
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
OMF3K = TOOLS.parent
ROOT = OMF3K.parent                                  # repository root

PROTOTYPE = OMF3K / "prototype"
DATA = OMF3K / "data"
WEB = OMF3K / "web"
SCRIPTS = OMF3K / "scripts"
DOCS = OMF3K / "docs"
ARTIFACTS = OMF3K / "build"                          # generated files, captures, reference images

CMAKE_BUILD = ROOT / "build"                         # OpenOMF's CMake and vcpkg build trees
VIEWER_DIR = CMAKE_BUILD / "omf_debug_z7"            # omf3d_prototype.exe, aftool.exe, rectool.exe, openomf.exe
TRACE_DIR = CMAKE_BUILD / "omf_trace_z7"             # openomf.exe with source tracing and the recorded traces
EXE = VIEWER_DIR / "omf3d_prototype.exe"
AFTOOL = VIEWER_DIR / "aftool.exe"
RECTOOL = VIEWER_DIR / "rectool.exe"

GAME_DATA = ROOT / "OMF2097"                         # the original game files (local, not distributed)
REMASTERED_HD = ROOT.parent / "OMF-2097-Remastered" / "public" / "hd"

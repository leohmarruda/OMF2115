"""Where everything lives, for the OMF2115 tools.

    project/prototype   C sources of the 3D viewer, with the tables generated for it next to them
    project/tools       Python tools (this folder)
    project/data        hand-kept catalogs: pose_catalog.csv, pose_sprite_groups.csv, move_names.csv
    project/web         page templates for the generated HTML tools
    project/scripts     PowerShell launchers
    project/docs        documentation
    project/build       everything the tools generate (ignored by git)
    build/            OpenOMF's own CMake and vcpkg trees, with the exes and the recorded traces

Tools get their locations from here instead of computing them, so a folder can move in one place.
"""
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
ROOT = PROJECT.parent                                  # repository root

PROTOTYPE = PROJECT / "prototype"
DATA = PROJECT / "data"
WEB = PROJECT / "web"
SCRIPTS = PROJECT / "scripts"
DOCS = PROJECT / "docs"
ARTIFACTS = PROJECT / "build"                          # generated files, captures, reference images

CMAKE_BUILD = ROOT / "build"                         # OpenOMF's CMake and vcpkg build trees
VIEWER_DIR = CMAKE_BUILD / "omf_debug_z7"            # omf3d_prototype.exe, aftool.exe, rectool.exe, openomf.exe
TRACE_DIR = CMAKE_BUILD / "omf_trace_z7"             # openomf.exe with source tracing and the recorded traces
EXE = VIEWER_DIR / "omf3d_prototype.exe"
AFTOOL = VIEWER_DIR / "aftool.exe"
RECTOOL = VIEWER_DIR / "rectool.exe"

GAME_DATA = ROOT / "OMF2097"                         # the original game files (local, not distributed)
REMASTERED_HD = ROOT.parent / "OMF-2097-Remastered" / "public" / "hd"

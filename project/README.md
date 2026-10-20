# OMF3K project workspace

This folder contains OMF3K-specific work inside the OpenOMF checkout. The upstream engine remains in the repository's `src/`, `resources/`, `testing/`, and other existing folders.

| Folder | Purpose |
| --- | --- |
| [docs](docs/README.md) | Roadmap, game specification, development plan, source baselines, story and reference material |
| [robots](robots/README.md) | Jaguar and Shadow approved modeling views and earlier concept exploration |
| [prototype](prototype/README.md) | C sources of the side-on 3D viewer and live/replay adapter, with the tables generated for it (pose catalog, blockout and Meshy meshes) |
| [tools](tools/paths.py) | Python tools: pose inventory and fitting, the pose editor and move browser generators, the catalog merge, mesh generators. `tools/paths.py` is the one place that knows where everything lives |
| [data](data) | Hand-kept catalogs: `pose_catalog.csv`, `pose_sprite_groups.csv`, `move_names.csv` |
| [web](web) | Page templates for the generated HTML tools (the pose editor) |
| [scripts](scripts) | PowerShell launchers for the viewer, the live fight and the Meshy preview |
| build | Everything the tools generate: reference sprites, the pose editor and move browser, captures, reports. Created on use and ignored by Git |

The approved [Jaguar](robots/jaguar/canonical/README.md) and [Shadow](robots/shadow/canonical/README.md) front, back, and right-side images are the current visual source of truth. Editable [Jaguar](robots/jaguar/blockout/README.md) and [Shadow](robots/shadow/blockout/README.md) blockouts now run in the prototype. The [recorded match review](docs/OMF3K_MODEL_MATCH_REVIEW.md) tracks their current reach, timing, facing, and readability gaps.

Local original-game files in `../OMF2097/`, generated sprite references in `docs/OMF2097/poses/` and `docs/Remastered/poses/`, generated files in `build/` here, OpenOMF's own CMake builds in `../build/`, and local dependencies in `../vcpkg_installed/` are not part of distributable OMF3K art. The two generated pose folders are ignored by Git.

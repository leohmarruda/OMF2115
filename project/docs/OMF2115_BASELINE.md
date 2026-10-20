# OMF2115 source baseline — 2026-10-09

This is the first reproducible Windows baseline for the 3D fidelity work. It
uses OpenOMF as the combat reference. The build outputs and copied original
game data are local to the ignored `build/` and `project/build/` directories.

## Environment

- Windows, Visual Studio 2022 Build Tools, MSVC 19.44.35222, CMake 3.31.6,
  Ninja, and the dependencies already installed in
  `build/vcpkg_installed/x64-windows`.
- Source version: OpenOMF `0.8.6-339-917e8070`.
- The local vcpkg manifest install cannot run in this workspace because access
  to `C:/Users/leohm/vcpkg` is denied. Configure with manifest mode disabled
  and point CMake to the existing installed dependencies.
- The default MSVC `/Zi` compiler check fails with `C1902: Program database
  manager mismatch`. Setting `/Z7` for Debug lets CMake configure and compile.

## Reproduce the Debug build

Run the following in a Visual Studio x64 Native Tools command prompt from the
repository root. Set `VCPKG_INSTALLED_DIR` to the absolute path of this
checkout's `build/vcpkg_installed` directory.

```bat
cmake -S . -B build/omf_debug_z7 -G Ninja ^
  -DCMAKE_TOOLCHAIN_FILE=C:/Users/leohm/vcpkg/scripts/buildsystems/vcpkg.cmake ^
  -DVCPKG_INSTALLED_DIR=C:/Users/leohm/AI_projects/OMF2115/build/vcpkg_installed ^
  -DVCPKG_MANIFEST_MODE=OFF -DCMAKE_BUILD_TYPE=Debug ^
  -DCMAKE_C_FLAGS_DEBUG="/Z7 /Ob0 /Od /RTC1" ^
  -DBUILD_3D_PROTOTYPE=OFF -DBUILD_LANGUAGES=ON -DUSE_TESTS=OFF
cmake --build build/omf_debug_z7 --parallel 4
```

The Release build also succeeds in `build/omf_ninja_z7` with
`-DCMAKE_C_FLAGS_RELEASE="/O2 /DNDEBUG /Z7"`. Its `openomf.exe --version`
reports the version above.

To run replays, copy the 55 files in the local `OMF2097/` directory into
`build/omf_debug_z7/resources/`. Keep those files out of source commits and
distribution packages. The build generates `ENGLISH.DAT2` when
`BUILD_LANGUAGES=ON`.

From the Debug build directory, set `OPENOMF_RESOURCE_PATH`,
`OPENOMF_STATE_PATH`, and `OPENOMF_CONFIG_PATH` to `.` and run, for example:

```bat
openomf.exe --force-audio-backend=NULL --force-renderer=NULL --speed=10 -P C:/Users/leohm/AI_projects/OMF2115/rectests/JAG-CORNER-THROW.REC
```

## Checks completed

| Check | Result |
| --- | --- |
| Fresh Release build and `--version` | Passed |
| Fresh Debug build with null audio and renderer | Passed |
| `JAG-CORNER-THROW.REC` | Passed, exit 0 |
| `STADIUM-WALL-SPLAT.REC` | Passed, exit 0 |
| `POWERPLANT-WALL-SPLAT.REC` | Passed, exit 0 |
| Existing 3D prototype `--self-test` | Passed |
| Stadium and Power Plant wall-state source traces | Passed; see [Stadium baseline](OMF2115_STADIUM_BASELINE.md) |
| Complete Jaguar–Shadow live-source trace replay | Passed, 472 frames; winner declared at tick 376 |

The `SHOULDFAIL.REC` fixture reached its expected assertion (`1994 != 2097`),
but the Windows process waited after reporting it and had to be interrupted.
That fixture is not counted as an automated pass.

## Remaining baseline work

- Enable CUnit and run the source unit tests. CUnit is absent from the local
  installed dependency set, and fetching it is currently blocked by vcpkg
  access. Do not treat the replay checks as a substitute for the unit suite.
- Complete a visible human-played match and capture reference frames, input
  settings, and timing observations for Jaguar and a contrasting HAR. The
  driven source trace establishes a complete result path, but not human input
  feel or visual readability.
- Inventory the first spike's assets and permissions before copying original
  game content into any shareable build.

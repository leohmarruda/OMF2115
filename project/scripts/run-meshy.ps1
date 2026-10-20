# Regenerate the Meshy meshes, rebuild the prototype and run it with the Robot
# Mascot standing in for Jaguar and the Rocket Jester for Shadow. By default this
# opens the model preview; -Fight starts a live OpenOMF match instead (fighter
# select screen, or pass -Har / -Pilot), and -Capture saves preview BMPs in project/build/.
param(
    [switch]$Fight,
    [ValidateSet('Jaguar', 'Shadow')]
    [string]$Har,
    [string]$Pilot,
    [switch]$Capture,
    [switch]$SkipGenerate,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
New-Item -ItemType Directory -Force (Join-Path $root 'project\build') | Out-Null   # where the viewer writes its captures
$buildDir = Join-Path $root "build\omf_debug_z7"
$exe = Join-Path $buildDir "omf3d_prototype.exe"
$vsDevCmd = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat"
$cmake = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"

if (-not $SkipGenerate) {
    python (Join-Path $root "project\tools\generate_meshy_meshes.py")
    if ($LASTEXITCODE -ne 0) { throw "generate_meshy_meshes.py failed" }
}

if (-not $SkipBuild) {
    cmd /c "`"$vsDevCmd`" -arch=x64 >nul && `"$cmake`" --build `"$buildDir`" --target omf3d_prototype"
    if ($LASTEXITCODE -ne 0) { throw "build failed" }
}

$env:OMF3K_MESHY = "1"
Push-Location $root
try {
    if ($Fight) {
        $live = @{}
        if ($Har) { $live.Har = $Har }
        if ($Pilot) { $live.Pilot = $Pilot }
        & (Join-Path $PSScriptRoot "run-live.ps1") @live
    } elseif ($Capture) { & $exe --model-preview-capture } else { & $exe --model-preview }
} finally {
    Pop-Location
    Remove-Item Env:\OMF3K_MESHY -ErrorAction SilentlyContinue
}

# Live fight as Shadow with the Meshy meshes (Robot Mascot for Jaguar, Rocket Jester
# for Shadow). Regenerates and rebuilds first; pass -SkipGenerate / -SkipBuild to skip.
param(
    [string]$Pilot,
    [switch]$SkipGenerate,
    [switch]$SkipBuild
)

$runArgs = @{ Fight = $true; Har = 'Shadow'; SkipGenerate = $SkipGenerate; SkipBuild = $SkipBuild }
if ($Pilot) { $runArgs.Pilot = $Pilot }
& (Join-Path $PSScriptRoot 'run-meshy.ps1') @runArgs
exit $LASTEXITCODE

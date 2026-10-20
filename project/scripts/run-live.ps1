param(
    [ValidateSet('Jaguar', 'Shadow')]
    [string]$Har,
    [ValidateSet('Crystal', 'Steffan', 'Milano', 'Christian', 'Shirro', 'JeanPaul', 'Ibrahim', 'Angel', 'Cossette', 'Raven')]
    [string]$Pilot,
    [ValidateRange(0, 3)]
    [int]$ShadowEnhancement = 0,
    [int]$CaptureTick = -1,
    [int]$WarmupSeconds = 4
)

$ErrorActionPreference = 'Stop'
$pilots = @('Crystal', 'Steffan', 'Milano', 'Christian', 'Shirro', 'JeanPaul', 'Ibrahim', 'Angel', 'Cossette', 'Raven')
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
New-Item -ItemType Directory -Force (Join-Path $projectRoot 'omf3k\build') | Out-Null   # where the viewer writes its captures
$sourceDir = Join-Path $projectRoot 'build\omf_trace_z7'
$viewerExe = Join-Path $projectRoot 'build\omf_debug_z7\omf3d_prototype.exe'

if (-not $Har -and -not $Pilot) {
    if (-not (Test-Path -LiteralPath $viewerExe)) { throw "Build omf3d_prototype first: $viewerExe" }
    $selectionPath = Join-Path $sourceDir ('omf3k-selection-' + [Guid]::NewGuid().ToString('N') + '.txt')
    $selector = Start-Process -FilePath $viewerExe -ArgumentList @('--select', $selectionPath) `
        -WorkingDirectory $projectRoot -PassThru
    $selector.WaitForExit()
    if (-not (Test-Path -LiteralPath $selectionPath)) { throw 'Fighter selection was cancelled.' }
    $selection = Get-Content -LiteralPath $selectionPath -Raw
    Remove-Item -LiteralPath $selectionPath -Force
    $harMatch = [regex]::Match($selection, '(?im)^har=(Jaguar|Shadow)\s*$')
    $pilotMatch = [regex]::Match($selection, '(?im)^pilot=(' + ($pilots -join '|') + ')\s*$')
    if (-not $harMatch.Success -or -not $pilotMatch.Success) { throw 'Fighter selection was cancelled.' }
    $Har = $harMatch.Groups[1].Value
    $Pilot = $pilotMatch.Groups[1].Value
} elseif (-not $Pilot) {
    $Pilot = if ($Har -eq 'Shadow') { 'Shirro' } else { 'Crystal' }
} elseif (-not $Har) {
    $Har = 'Jaguar'
}
& (Join-Path $PSScriptRoot 'run-live-jaguar.ps1') -Player $Har -Pilot $Pilot `
    -ShadowEnhancement $ShadowEnhancement -CaptureTick $CaptureTick `
    -WarmupSeconds $WarmupSeconds
exit $LASTEXITCODE

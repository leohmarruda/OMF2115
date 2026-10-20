param(
    [int]$CaptureTick = -1,
    [int]$WarmupSeconds = 4,
    [ValidateSet('Jaguar', 'Shadow')]
    [string]$Player = 'Jaguar',
    [ValidateSet('Crystal', 'Steffan', 'Milano', 'Christian', 'Shirro', 'JeanPaul', 'Ibrahim', 'Angel', 'Cossette', 'Raven')]
    [string]$Pilot = '',
    # Original Tournament upgrade level for Shadow (0-3). Shadow's shadow attacks,
    # such as Shadow Punch, only exist in the original data at level 3.
    [ValidateRange(0, 3)]
    [int]$ShadowEnhancement = 0
)

$ErrorActionPreference = 'Stop'
if ($CaptureTick -lt -1) { throw 'CaptureTick must be zero or greater.' }
if ($WarmupSeconds -lt 0 -or $WarmupSeconds -gt 8) { throw 'WarmupSeconds must be between zero and eight.' }
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
New-Item -ItemType Directory -Force (Join-Path $projectRoot 'project\build') | Out-Null   # where the viewer writes its captures
$sourceDir = Join-Path $projectRoot 'build\omf_trace_z7'
$sourceExe = Join-Path $sourceDir 'openomf.exe'
$viewerExe = Join-Path $projectRoot 'build\omf_debug_z7\omf3d_prototype.exe'
$tracePath = Join-Path $sourceDir 'omf3k-live.csv'

if (-not (Test-Path -LiteralPath $sourceExe)) { throw "Build OpenOMF with OMF3K_SOURCE_TRACE=ON first: $sourceExe" }
if (-not (Test-Path -LiteralPath $viewerExe)) { throw "Build omf3d_prototype first: $viewerExe" }
if (-not (Test-Path -LiteralPath (Join-Path $sourceDir 'resources\ARENA0.BK'))) {
    throw "OpenOMF resources are missing in $sourceDir"
}

$env:OMF3K_TRACE_PATH = $null
$env:OMF3K_INPUT_PATH = $null
$env:OMF3K_LIVE_PLAYER = $Player
$pilotNames = @('Crystal', 'Steffan', 'Milano', 'Christian', 'Shirro', 'JeanPaul', 'Ibrahim', 'Angel', 'Cossette', 'Raven')
if ($Pilot -eq '') { $Pilot = if ($Player -eq 'Shadow') { 'Shirro' } else { 'Crystal' } }
$Pilot = $pilotNames | Where-Object { $_ -ieq $Pilot } | Select-Object -First 1
$env:OMF3K_LIVE_PILOT_ID = [string][array]::IndexOf($pilotNames, $Pilot)
$env:OMF3K_LIVE_PILOT_NAME = $Pilot.ToUpperInvariant()
$env:OMF3K_LIVE_RIVAL_NAME = if ($Player -eq 'Shadow') { 'CRYSTAL' } else { 'SHIRRO' }
$env:OMF3K_SHADOW_ENHANCEMENT = [string]$ShadowEnhancement
Write-Host "Starting $Pilot / $Player in Stadium"
$env:OMF3K_INPUT_MAP = 'Local\OMF3KInput_' + [Guid]::NewGuid().ToString('N')
$env:OMF3K_STATE_MAP = 'Local\OMF3KState_' + [Guid]::NewGuid().ToString('N')
$viewerArgs = @('--source-live', $tracePath)
if ($CaptureTick -ge 0) { $viewerArgs += @('--capture-tick', [string]$CaptureTick) }
$viewerOut = Join-Path $sourceDir 'omf3k-live-viewer-out.txt'
$viewerErr = Join-Path $sourceDir 'omf3k-live-viewer-err.txt'
$sourceOut = Join-Path $sourceDir 'omf3k-live-source-out.txt'
$sourceErr = Join-Path $sourceDir 'omf3k-live-source-err.txt'
$source = $null
$viewer = $null
$viewerExit = 1
try {
    if ($WarmupSeconds -gt 0) {
        $viewer = Start-Process -FilePath $viewerExe -ArgumentList $viewerArgs `
            -WorkingDirectory $projectRoot `
            -RedirectStandardOutput $viewerOut `
            -RedirectStandardError $viewerErr `
            -PassThru
        Start-Sleep -Seconds $WarmupSeconds
        $viewer.Refresh()
        if ($viewer.HasExited) { throw "3D viewer exited during startup (code $($viewer.ExitCode))." }
    }
    $source = Start-Process -FilePath $sourceExe `
        -ArgumentList @('--omf3k-live', '--force-audio-backend=NULL', '--force-renderer=NULL', '--speed=5', '--log-level=WARN') `
        -WorkingDirectory $sourceDir `
        -RedirectStandardOutput $sourceOut `
        -RedirectStandardError $sourceErr `
        -WindowStyle Hidden -PassThru
    Start-Sleep -Milliseconds 500
    $source.Refresh()
    if ($source.HasExited) { throw "OpenOMF exited during startup (code $($source.ExitCode)). Check omf3k-live-source-err.txt." }

    if ($viewer) {
        $viewer.WaitForExit()
        $viewerExit = $viewer.ExitCode
        Get-Content -LiteralPath $viewerOut
        if ($viewerExit -ne 0) { Get-Content -LiteralPath $viewerErr }
    } else {
        Push-Location $projectRoot
        try {
            & $viewerExe @viewerArgs
            $viewerExit = $LASTEXITCODE
        } finally {
            Pop-Location
        }
    }
} finally {
    if ($viewer) {
        $viewer.Refresh()
        if (-not $viewer.HasExited) { Stop-Process -Id $viewer.Id }
    }
    if ($source) {
        $source.Refresh()
        if (-not $source.HasExited) { Stop-Process -Id $source.Id }
    }
}
exit $viewerExit

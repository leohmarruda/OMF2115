param(
    [int]$CaptureTick = -1,
    [int]$WarmupSeconds = 4,
    [ValidateSet('Crystal', 'Steffan', 'Milano', 'Christian', 'Shirro', 'JeanPaul', 'Ibrahim', 'Angel', 'Cossette', 'Raven')]
    [string]$Pilot = 'Shirro',
    [ValidateRange(0, 3)]
    [int]$ShadowEnhancement = 0
)

& (Join-Path $PSScriptRoot 'run-live-jaguar.ps1') `
    -Player Shadow -Pilot $Pilot -CaptureTick $CaptureTick -WarmupSeconds $WarmupSeconds `
    -ShadowEnhancement $ShadowEnhancement
exit $LASTEXITCODE

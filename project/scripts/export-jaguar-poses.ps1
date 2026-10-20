param(
    [string]$OutputDirectory = 'omf3k/docs/OMF2097/poses/jaguar'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$tool = Join-Path $root 'build/omf_debug_z7/aftool.exe'
$fighter = Join-Path $root 'OMF2097/FIGHTR0.AF'
$palette = Join-Path $root 'OMF2097/ARENA0.BK'
foreach ($required in @($tool, $fighter, $palette)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required local file is missing: $required" }
}
$destination = [System.IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
New-Item -ItemType Directory -Force -Path $destination | Out-Null

$poses = @(
    @('01-idle', 'Idle stance', 11, 0, 'Neutral silhouette and armor proportions'),
    @('02-walk', 'Walking', 10, 3, 'Forward movement and weight shift'),
    @('03-jump', 'Jumping', 1, 3, 'Compact airborne silhouette'),
    @('04-crouch', 'Crouching', 4, 0, 'Low stance and compressed legs'),
    @('05-block-high', 'Standing guard', 5, 0, 'Raised arms protecting the head'),
    @('06-block-low', 'Crouching guard', 6, 0, 'Low defense and compact silhouette'),
    @('07-punch', 'Standing punch', 42, 3, 'Extended arm and upper-body strike'),
    @('08-kick', 'Standing kick', 41, 3, 'High leg extension and balance'),
    @('09-low-punch', 'Low punch', 30, 3, 'Forward lunge at crouch height'),
    @('10-throw', 'Close throw', 20, 3, 'Grappling body lean'),
    @('11-hit', 'Taking a hit', 9, 5, 'Impact recoil'),
    @('12-victory', 'Victory', 48, 7, 'Celebration silhouette'),
    @('13-defeat', 'Defeat', 49, 3, 'Fallen body pose'),
    @('14-special', 'Special move', 21, 2, 'Concussion-cannon move pose'),
    @('15-low-kick', 'Low kick', 19, 2, 'Sweeping leg extension'),
    @('16-air-attack', 'Air attack', 15, 2, 'Long airborne strike')
)

$lines = @(
    '# Jaguar pose references',
    '',
    'Exact original side-view sprite frames extracted from local `FIGHTR0.AF` with the `ARENA0.BK` palette. These are reference images for redesign, not improved artwork. Original game data stays local in this ignored documentation folder.',
    '',
    '| Pose | Original frame | Picture | Redesign focus |',
    '| --- | --- | --- | --- |'
)
foreach ($pose in $poses) {
    $file = "$($pose[0]).png"
    $target = Join-Path $destination $file
    & $tool -f $fighter -p $palette -m $pose[2] -s $pose[3] --export-png $target | Out-Null
    if (-not (Test-Path -LiteralPath $target)) { throw "Sprite export failed: $file" }
    $lines += "| $($pose[1]) | Animation $($pose[2]), sprite $($pose[3]) | ![$($pose[1])]($file) | $($pose[4]) |"
}
$lines += @(
    '',
    'All images show the original side view. A 3D model also needs new front, back, and three-quarter turnarounds, plus close views of the head, chest, hands, and feet.'
)
[System.IO.File]::WriteAllLines((Join-Path $destination 'index.md'), $lines, [System.Text.UTF8Encoding]::new($false))
Write-Output "Saved $($poses.Count) Jaguar poses and index to $destination"

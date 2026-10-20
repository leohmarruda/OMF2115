param(
    [ValidateSet('All','Jaguar','Shadow','Thorn','Pyros','Electra','Katana','Shredder','Flail','Gargoyle','Chronos','Nova')]
    [string]$Robot = 'All',
    [string]$OutputDirectory = 'project/docs/OMF2097/poses'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$tool = Join-Path $root 'build/omf_debug_z7/aftool.exe'
$palette = Join-Path $root 'OMF2097/ARENA0.BK'
foreach ($required in @($tool, $palette)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required local file is missing: $required" }
}
$destination = [System.IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
New-Item -ItemType Directory -Force -Path $destination | Out-Null

# Attack IDs were checked against each AF file's input strings and categories.
# Common animation IDs (1..11, 48, 49) are shared across the roster.
$roster = @(
    @{ Name='Jaguar';   Id=0;  Punch=42; Kick=41; LowPunch=30; Throw=20; Special=21; LowKick=19; Air=15 },
    @{ Name='Shadow';   Id=1;  Punch=43; Kick=42; LowPunch=36; Throw=20; Special=23; LowKick=18; Air=44 },
    @{ Name='Thorn';    Id=2;  Punch=42; Kick=41; LowPunch=30; Throw=20; Special=34; LowKick=19; Air=15 },
    @{ Name='Pyros';    Id=3;  Punch=42; Kick=41; LowPunch=21; Throw=26; Special=17; LowKick=19; Air=22 },
    @{ Name='Electra';  Id=4;  Punch=43; Kick=41; LowPunch=17; Throw=42; Special=22; LowKick=19; Air=37 },
    @{ Name='Katana';   Id=5;  Punch=42; Kick=41; LowPunch=16; Throw=33; Special=21; LowKick=18; Air=24 },
    @{ Name='Shredder'; Id=6;  Punch=42; Kick=41; LowPunch=30; Throw=28; Special=21; LowKick=23; Air=25 },
    @{ Name='Flail';    Id=7;  Punch=42; Kick=41; LowPunch=16; Throw=23; Special=26; LowKick=18; Air=22 },
    @{ Name='Gargoyle'; Id=8;  Punch=42; Kick=41; LowPunch=16; Throw=34; Special=21; LowKick=18; Air=24 },
    @{ Name='Chronos';  Id=9;  Punch=42; Kick=41; LowPunch=30; Throw=22; Special=18; LowKick=19; Air=29 },
    @{ Name='Nova';     Id=10; Punch=43; Kick=42; LowPunch=39; Throw=24; Special=31; LowKick=18; Air=40 }
)

$selected = @($roster | Where-Object { $Robot -eq 'All' -or $_.Name -eq $Robot })
$master = @(
    '# Original robot pose references',
    '',
    'Exact side-view frames extracted from the local One Must Fall 2097 robot files with the Stadium palette. These are references for redesigned artwork, not improved drawings. The images stay in this locally ignored documentation folder.',
    '',
    '| Robot | Neutral | Punch | Distinctive move | Full pose list |',
    '| --- | --- | --- | --- | --- |'
)

foreach ($entry in $selected) {
    $name = $entry.Name
    $slug = $name.ToLowerInvariant()
    $fighter = Join-Path $root "OMF2097/FIGHTR$($entry.Id).AF"
    if (-not (Test-Path -LiteralPath $fighter)) { throw "Robot data is missing: $fighter" }
    $folder = Join-Path $destination $slug
    New-Item -ItemType Directory -Force -Path $folder | Out-Null

    $spriteCounts = @{}
    $currentMove = -1
    foreach ($line in (& $tool -f $fighter -A)) {
        if ($line -match '^Move #(\d+) information:') { $currentMove = [int]$matches[1] }
        if ($line -match '^\s*\* Sprites:\s+(\d+)') { $spriteCounts[$currentMove] = [int]$matches[1] }
    }

    $poses = @(
        @('01-idle','Idle stance',11,0,'Neutral silhouette and armor proportions'),
        @('02-walk','Walking',10,3,'Forward movement and weight shift'),
        @('03-jump','Jumping',1,3,'Airborne silhouette'),
        @('04-crouch','Crouching',4,0,'Low stance and compressed legs'),
        @('05-block-high','Standing guard',5,0,'Raised defense'),
        @('06-block-low','Crouching guard',6,0,'Compact low defense'),
        @('07-punch','Standing punch',$entry.Punch,3,'Extended upper-body strike'),
        @('08-kick','Standing kick',$entry.Kick,3,'Leg extension and balance'),
        @('09-low-punch','Low punch',$entry.LowPunch,3,'Attack at crouch height'),
        @('10-throw','Close throw',$entry.Throw,3,'Grappling pose'),
        @('11-hit','Taking a hit',9,5,'Impact recoil'),
        @('12-victory','Victory',48,7,'Celebration silhouette'),
        @('13-defeat','Defeat',49,3,'Fallen or defeated pose'),
        @('14-special','Distinctive move',$entry.Special,2,'Robot-specific move silhouette'),
        @('15-low-kick','Low kick',$entry.LowKick,2,'Sweeping leg extension'),
        @('16-air-attack','Air attack',$entry.Air,2,'Airborne strike silhouette')
    )
    $lines = @(
        "# $name pose references",
        '',
        "Original side-view frames from ``FIGHTR$($entry.Id).AF``. Sprite indices are capped to the available frames in each animation.",
        '',
        '| Pose | Original frame | Picture | Redesign focus |',
        '| --- | --- | --- | --- |'
    )
    foreach ($pose in $poses) {
        $move = [int]$pose[2]
        if (-not $spriteCounts.ContainsKey($move) -or $spriteCounts[$move] -lt 1) {
            throw "$name animation $move has no sprites"
        }
        $sprite = [Math]::Min([int]$pose[3], $spriteCounts[$move] - 1)
        $file = "$($pose[0]).png"
        $target = Join-Path $folder $file
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target }
        $result = & $tool -f $fighter -p $palette -m $move -s $sprite --export-png $target
        if (-not (Test-Path -LiteralPath $target)) { throw "PNG export failed for $name $($pose[1]): $result" }
        $lines += "| $($pose[1]) | Animation $move, sprite $sprite | ![$name $($pose[1])]($file) | $($pose[4]) |"
    }
    $lines += @('', 'These original sprites show only the side view. The 3D design also needs newly drawn front, back, and three-quarter views.')
    [System.IO.File]::WriteAllLines((Join-Path $folder 'index.md'), $lines, [System.Text.UTF8Encoding]::new($false))
    $master += "| $name | ![$name idle]($slug/01-idle.png) | ![$name punch]($slug/07-punch.png) | ![$name special]($slug/14-special.png) | [16 poses]($slug/index.md) |"
    Write-Output "Exported ${name}: $($poses.Count) poses"
}
$master += @('', 'A full 3D turnaround requires new artwork beyond these original side-view frames.')
[System.IO.File]::WriteAllLines((Join-Path $destination 'index.md'), $master, [System.Text.UTF8Encoding]::new($false))
Write-Output "Saved roster index to $destination"

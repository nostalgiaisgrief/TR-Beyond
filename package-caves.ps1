param([string]$Name = 'caves-playtest-01')
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[a-z0-9][a-z0-9-]{0,63}$') { throw 'Use a simple lowercase package name.' }
$destination = Join-Path $PSScriptRoot "dist\$Name"
$archive = Join-Path $PSScriptRoot "dist\$Name.zip"
if ((Test-Path -LiteralPath $destination) -or (Test-Path -LiteralPath $archive)) { throw 'Package already exists; choose a new Name to preserve it.' }
$files = @('build\tomb_preview.exe','work\reference-assets\sine.bin')
$files += Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'work\reference-assets\DATA') -Filter '*.PHD' | Where-Object { $_.Name -in @('GYM.PHD','TITLE.PHD') -or $_.Name -like 'LEVEL*.PHD' } | ForEach-Object { 'work\reference-assets\DATA\' + $_.Name }
$files += 'work\reference-assets\DATA\TITLEH.PCX'
$files += Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'work\reference-assets\audio') -Filter '*.wav' | ForEach-Object { 'work\reference-assets\audio\' + $_.Name }
foreach ($relative in $files) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) { throw "Missing required file: $relative" }
}
foreach ($relative in $files) {
    $target = Join-Path $destination $relative
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $target
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'launch-caves.cmd') -Destination (Join-Path $destination 'Play.cmd')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'choose-level.cmd') -Destination (Join-Path $destination 'Choose-level.cmd')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'CAVES-PLAYTEST.txt') -Destination (Join-Path $destination 'PLAYTEST.txt')
$manifest = foreach ($relative in $files) {
    $file = Join-Path $destination $relative
    [pscustomobject]@{path=$relative;bytes=(Get-Item -LiteralPath $file).Length;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $destination 'manifest.json') -Encoding utf8
Compress-Archive -LiteralPath $destination -DestinationPath $archive
Write-Output "Packaged $destination"
Write-Output "Archive $archive"

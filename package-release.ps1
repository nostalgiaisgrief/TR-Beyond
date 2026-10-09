param(
    [string]$Name = 'TR-Beyond-playtest-26-windows-x64',
    [string]$Executable = 'dist/caves-playtest-26/build/tomb_preview.exe'
)
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,80}$') { throw 'Invalid release name.' }
$destination = Join-Path $PSScriptRoot "dist\$Name"
$archive = "$destination.zip"
if ((Test-Path -LiteralPath $destination) -or (Test-Path -LiteralPath $archive)) {
    throw 'Release output exists; choose a new name.'
}
$files = @{
    'build/tomb_preview.exe' = $Executable
    'Play.cmd' = 'launch-caves.cmd'
    'Choose-level.cmd' = 'choose-level.cmd'
    'README.md' = 'README.md'
    'HISTORY.MD' = 'HISTORY.MD'
    'CAVES-PLAYTEST.txt' = 'CAVES-PLAYTEST.txt'
    'tools/prepare_assets.py' = 'tools/prepare_assets.py'
    'tools/inspect_reference.py' = 'tools/inspect_reference.py'
}
foreach ($source in $files.Values) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $source) -PathType Leaf)) {
        throw "Missing release input: $source"
    }
}
# Only this explicit list is copied: never copy an existing playtest directory.
foreach ($relative in $files.Keys) {
    $target = Join-Path $destination $relative
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $files[$relative]) -Destination $target
}
$manifest = foreach ($relative in ($files.Keys | Sort-Object)) {
    $path = Join-Path $destination $relative
    [pscustomobject]@{path=$relative;bytes=(Get-Item -LiteralPath $path).Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $destination 'manifest.json') -Encoding utf8
Compress-Archive -Path (Join-Path $destination '*') -DestinationPath $archive
$checksum = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
"$checksum  $Name.zip" | Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
Write-Output "Packaged asset-free release: $archive"

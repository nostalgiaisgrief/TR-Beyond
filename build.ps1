param([switch]$Debug)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$compiler = Join-Path $projectRoot 'work\toolchain\zig-x86_64-windows-0.15.2\zig.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Portable Zig 0.15.2 is missing; see tests/README.md.' }
$env:ZIG_GLOBAL_CACHE_DIR = Join-Path $projectRoot 'work\zig-global-cache'
$env:ZIG_LOCAL_CACHE_DIR = Join-Path $projectRoot 'work\zig-local-cache'
$buildDir = Join-Path $projectRoot 'build'
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
$outputName = if ($Debug) { 'movement_test_debug.exe' } else { 'movement_test.exe' }
$optimization = if ($Debug) { '-O0' } else { '-O2' }
$arguments = @('cc', '-target', 'x86_64-windows-gnu', '-std=c11', $optimization,
    '-g', '-Wall', '-Wextra', '-Werror', '-pedantic',
    '-I', (Join-Path $projectRoot 'src'),
    (Join-Path $projectRoot 'src\movement.c'),
    (Join-Path $projectRoot 'tests\movement_runner.c'),
    '-o', (Join-Path $buildDir $outputName))
& $compiler @arguments
if ($LASTEXITCODE -ne 0) { throw "C compilation failed: $LASTEXITCODE" }
Write-Output "Built $outputName"
$libraryName = if ($Debug) { 'step_test_debug.dll' } else { 'step_test.dll' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -shared `
    -I (Join-Path $projectRoot 'src') `
    (Join-Path $projectRoot 'src\ui_dialog.c') `
    (Join-Path $projectRoot 'src\interface.c') `
    (Join-Path $projectRoot 'src\ring.c') `
    (Join-Path $projectRoot 'src\text.c') `
    (Join-Path $projectRoot 'src\inventory.c') `
    (Join-Path $projectRoot 'src\pickup.c') `
    (Join-Path $projectRoot 'src\progression.c') `
    (Join-Path $projectRoot 'src\combat.c') `
    (Join-Path $projectRoot 'src\enemies.c') `
    (Join-Path $projectRoot 'src\creature_move.c') `
    (Join-Path $projectRoot 'src\navigation.c') `
    (Join-Path $projectRoot 'src\creature.c') `
    (Join-Path $projectRoot 'src\pistols.c') `
    (Join-Path $projectRoot 'src\hazards.c') `
    (Join-Path $projectRoot 'src\preview_camera.c') `
    (Join-Path $projectRoot 'src\dos_camera.c') `
    (Join-Path $projectRoot 'src\objects.c') `
    (Join-Path $projectRoot 'src\city.c') `
    (Join-Path $projectRoot 'src\object_contact.c') `
    (Join-Path $projectRoot 'src\slide.c') `
    (Join-Path $projectRoot 'src\air.c') `
    (Join-Path $projectRoot 'src\gym.c') `
    (Join-Path $projectRoot 'src\sound.c') `
    (Join-Path $projectRoot 'src\follow_camera.c') `
    (Join-Path $projectRoot 'src\ledge.c') `
    (Join-Path $projectRoot 'src\water.c') `
    (Join-Path $projectRoot 'src\ground.c') `
    (Join-Path $projectRoot 'src\animation.c') `
    (Join-Path $projectRoot 'src\collision.c') `
    (Join-Path $projectRoot 'src\level.c') `
    (Join-Path $projectRoot 'src\geometry.c') `
    (Join-Path $projectRoot 'src\terrain.c') `
    (Join-Path $projectRoot 'src\static.c') `
    (Join-Path $projectRoot 'src\item_height.c') `
    (Join-Path $projectRoot 'src\lara_start.c') `
    (Join-Path $projectRoot 'src\visual.c') `
    (Join-Path $projectRoot 'tests\step_bridge.c') `
    -o (Join-Path $buildDir $libraryName)
if ($LASTEXITCODE -ne 0) { throw "Animation/collision compilation failed: $LASTEXITCODE" }
Write-Output "Built $libraryName"

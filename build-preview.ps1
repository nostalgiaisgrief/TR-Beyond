param([switch]$Debug)
$ErrorActionPreference = 'Stop'
$env:ZIG_GLOBAL_CACHE_DIR = Join-Path $PSScriptRoot 'work\zig-global-cache'
$env:ZIG_LOCAL_CACHE_DIR = Join-Path $PSScriptRoot 'work\zig-local-cache'
$compiler = Join-Path $PSScriptRoot 'work\toolchain\zig-x86_64-windows-0.15.2\zig.exe'
$optimization = if ($Debug) { '-O0' } else { '-O2' }
$outputName = if ($Debug) { 'tomb_preview_debug.exe' } else { 'tomb_preview.exe' }
$sourceNames = @('enemies.c','creature_move.c','navigation.c','creature.c','pistols.c','hazards.c','dos_camera.c','object_contact.c','objects.c','slide.c','sound_win.c','sound.c','preview.c','room_visibility.c','gym.c','follow_camera.c','air.c','water.c','ledge.c','playtest.c','movement.c','animation.c','ground.c','collision.c','terrain.c','static.c','preview_pose.c','preview_camera.c','level.c','visual.c','lara_start.c','geometry.c','item_height.c')
$sourceNames += 'ui_dialog.c','save.c','city.c','combat.c','combat_fixture.c','interface.c','ring.c','text.c','inventory.c','pickup.c','pickup_runtime.c','progression.c'
$sources = $sourceNames | ForEach-Object { Join-Path $PSScriptRoot "src\$_" }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic @sources -lopengl32 -lgdi32 -luser32 -lwinmm -lavrt '-Wl,--subsystem,windows' -o (Join-Path $PSScriptRoot "build\$outputName")
if ($LASTEXITCODE -ne 0) { throw "Preview compilation failed: $LASTEXITCODE" }
Write-Output "Built $outputName"



$cameraTest = if ($Debug) { 'preview_camera_test_debug.exe' } else { 'preview_camera_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') (Join-Path $PSScriptRoot 'src\preview_camera.c') (Join-Path $PSScriptRoot 'tests\preview_camera_test.c') -o (Join-Path $PSScriptRoot "build\$cameraTest")
if ($LASTEXITCODE -ne 0) { throw "Camera test compilation failed: $LASTEXITCODE" }
& (Join-Path $PSScriptRoot "build\$cameraTest")
if ($LASTEXITCODE -ne 0) { throw "Camera orientation test failed: $LASTEXITCODE" }

$playtestName = if ($Debug) { 'playtest_test_debug.exe' } else { 'playtest_test.exe' }
$playtestSources = $sources | Where-Object { [IO.Path]::GetFileName($_) -notin @('preview.c','sound_win.c') }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'tests\playtest_test.c') -o (Join-Path $PSScriptRoot "build\$playtestName")
if ($LASTEXITCODE -ne 0) { throw "Ground integration test compilation failed: $LASTEXITCODE" }
& (Join-Path $PSScriptRoot "build\$playtestName") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\GYM.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\sine.bin')
if ($LASTEXITCODE -ne 0) { throw "Ground integration test failed: $LASTEXITCODE" }

$poseTest = if ($Debug) { 'preview_pose_test_debug.exe' } else { 'preview_pose_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'tests\preview_pose_test.c') -o (Join-Path $PSScriptRoot "build\$poseTest")
if ($LASTEXITCODE -ne 0) { throw "Pose test compilation failed: $LASTEXITCODE" }
& (Join-Path $PSScriptRoot "build\$poseTest") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\GYM.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\DATA\LEVEL1.PHD')
if ($LASTEXITCODE -ne 0) { throw "Pose interpolation validation failed: $LASTEXITCODE" }

$followTest = if ($Debug) { 'follow_camera_test_debug.exe' } else { 'follow_camera_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'tests\follow_camera_test.c') -o (Join-Path $PSScriptRoot "build\$followTest")
if ($LASTEXITCODE -ne 0) { throw "Follow camera compilation failed: $LASTEXITCODE" }
& (Join-Path $PSScriptRoot "build\$followTest") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\GYM.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\sine.bin')
if ($LASTEXITCODE -ne 0) { throw "Follow camera validation failed: $LASTEXITCODE" }

$visibilityTest = if ($Debug) { 'room_visibility_test_debug.exe' } else { 'room_visibility_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') (Join-Path $PSScriptRoot 'src\room_visibility.c') (Join-Path $PSScriptRoot 'src\preview_camera.c') (Join-Path $PSScriptRoot 'tests\room_visibility_test.c') -o (Join-Path $PSScriptRoot "build\$visibilityTest")
if ($LASTEXITCODE -ne 0) { throw 'Visibility test compilation failed' }
& (Join-Path $PSScriptRoot "build\$visibilityTest")
if ($LASTEXITCODE -ne 0) { throw 'Visibility test failed' }

$soundTest = if ($Debug) { 'sound_test_debug.exe' } else { 'sound_test.exe' }
$soundSuffix = if ($Debug) { '_debug' } else { '' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'src\sound_win.c') (Join-Path $PSScriptRoot 'tests\sound_test.c') -lwinmm -lavrt -o (Join-Path $PSScriptRoot "build\$soundTest")
if ($LASTEXITCODE -ne 0) { throw 'Sound test compilation failed' }
& (Join-Path $PSScriptRoot "build\$soundTest") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\GYM.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\sine.bin') (Join-Path $PSScriptRoot "build\gym-sounds$soundSuffix.wav") (Join-Path $PSScriptRoot "build\gym-sounds$soundSuffix.txt")
if ($LASTEXITCODE -ne 0) { throw 'Sound integration test failed' }

$cavesTest = if ($Debug) { 'caves_test_debug.exe' } else { 'caves_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'tests\caves_test.c') -o (Join-Path $PSScriptRoot "build\$cavesTest")
if ($LASTEXITCODE -ne 0) { throw 'Caves test compilation failed' }
& (Join-Path $PSScriptRoot "build\$cavesTest") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\LEVEL1.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\sine.bin')
if ($LASTEXITCODE -ne 0) { throw 'Caves movement validation failed' }

# Exercise Windows key-message routing as well as fixture/camera gameplay.
foreach ($inputArgs in @('--window-input-test','--window-input-test --caves')) {
    $inputProcess = Start-Process -FilePath (Join-Path $PSScriptRoot "build\$outputName") -ArgumentList $inputArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -Wait -PassThru
    if ($inputProcess.ExitCode -ne 0) { throw "Window input integration failed: $inputArgs" }
}
Write-Output 'PASS: gym/Caves Windows input and switch camera integration'

$combatTest = if ($Debug) { 'combat_test_debug.exe' } else { 'combat_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'tests\combat_test.c') -o (Join-Path $PSScriptRoot "build\$combatTest")
if ($LASTEXITCODE -ne 0) { throw 'Combat test compilation failed' }
& (Join-Path $PSScriptRoot "build\$combatTest") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\LEVEL1.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\sine.bin')
if ($LASTEXITCODE -ne 0) { throw 'Combat integration failed' }

$inventoryTest = if ($Debug) { 'inventory_test_debug.exe' } else { 'inventory_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'tests\inventory_test.c') -o (Join-Path $PSScriptRoot "build\$inventoryTest")
if ($LASTEXITCODE -ne 0) { throw 'Inventory test compilation failed' }
& (Join-Path $PSScriptRoot "build\$inventoryTest") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\LEVEL1.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\sine.bin') (Join-Path $PSScriptRoot 'work\reference-assets\DATA\LEVEL2.PHD')
if ($LASTEXITCODE -ne 0) { throw 'Inventory/progression integration failed' }

$cityTest = if ($Debug) { 'city_test_debug.exe' } else { 'city_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'tests\city_test.c') -o (Join-Path $PSScriptRoot "build\$cityTest")
if ($LASTEXITCODE -ne 0) { throw 'City test compilation failed' }
& (Join-Path $PSScriptRoot "build\$cityTest") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\LEVEL2.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\sine.bin')
if ($LASTEXITCODE -ne 0) { throw 'City integration failed' }

$questProcess = Start-Process -FilePath (Join-Path $PSScriptRoot "build\$outputName") -ArgumentList '--city --quest-ui-test' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -Wait -PassThru
if ($questProcess.ExitCode -ne 0) { throw "Quest UI integration failed: $($questProcess.ExitCode)" }
Write-Output 'PASS: City quest menu, S/Enter selection, door completion and main/items ring navigation'

$cityTransition = Start-Process -FilePath (Join-Path $PSScriptRoot "build\$outputName") -ArgumentList '--city --transition-test --capture build/city-transition-check.ppm' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -Wait -PassThru
if ($cityTransition.ExitCode -ne 0) { throw "City to Lost Valley transition failed: $($cityTransition.ExitCode)" }
Write-Output 'PASS: City actual exit, Enter continuation, Lost Valley load, inventory carry and level-state reset'

$saveTest = if ($Debug) { 'save_test_debug.exe' } else { 'save_test.exe' }
& $compiler cc -target x86_64-windows-gnu -std=c11 $optimization -g -Wall -Wextra -Werror -pedantic -I (Join-Path $PSScriptRoot 'src') @playtestSources (Join-Path $PSScriptRoot 'tests\save_test.c') -o (Join-Path $PSScriptRoot "build\$saveTest")
if ($LASTEXITCODE -ne 0) { throw 'Save test compilation failed' }
& (Join-Path $PSScriptRoot "build\$saveTest") (Join-Path $PSScriptRoot 'work\reference-assets\DATA\LEVEL1.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\DATA\LEVEL2.PHD') (Join-Path $PSScriptRoot 'work\reference-assets\sine.bin')
if ($LASTEXITCODE -ne 0) { throw 'Save state test failed' }
$frontProcess = Start-Process -FilePath (Join-Path $PSScriptRoot "build\$outputName") -ArgumentList '--frontend-test' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -Wait -PassThru
if ($frontProcess.ExitCode -ne 0) { throw 'Front-end menu integration failed; see build/frontend-test.txt' }
Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build\frontend-test.txt')

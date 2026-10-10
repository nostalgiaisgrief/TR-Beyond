param([string]$Python = '')
$ErrorActionPreference = 'Stop'
if (-not $Python) {
    $bundledPython = 'C:\Users\richa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    $Python = if (Test-Path -LiteralPath $bundledPython) { $bundledPython } else { 'python' }
}
& (Join-Path $PSScriptRoot 'build.ps1')
& (Join-Path $PSScriptRoot 'build.ps1') -Debug
& $Python (Join-Path $PSScriptRoot 'tests\compare_original.py') --exe `
    (Join-Path $PSScriptRoot 'build\movement_test.exe') `
    (Join-Path $PSScriptRoot 'build\movement_test_debug.exe')
if ($LASTEXITCODE -ne 0) { throw "Differential validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_step.py') --dll `
    (Join-Path $PSScriptRoot 'build\step_test.dll') `
    (Join-Path $PSScriptRoot 'build\step_test_debug.dll')
if ($LASTEXITCODE -ne 0) { throw "Animation/collision validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_level.py') --dll `
    (Join-Path $PSScriptRoot 'build\step_test.dll') `
    (Join-Path $PSScriptRoot 'build\step_test_debug.dll')
if ($LASTEXITCODE -ne 0) { throw "Real-level validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_terrain.py') --dll `
    (Join-Path $PSScriptRoot 'build\step_test.dll') `
    (Join-Path $PSScriptRoot 'build\step_test_debug.dll')
if ($LASTEXITCODE -ne 0) { throw "Terrain contact validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_static.py') --dll `
    (Join-Path $PSScriptRoot 'build\step_test.dll') `
    (Join-Path $PSScriptRoot 'build\step_test_debug.dll')
if ($LASTEXITCODE -ne 0) { throw "Static contact validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_items.py') --dll `
    (Join-Path $PSScriptRoot 'build\step_test.dll') `
    (Join-Path $PSScriptRoot 'build\step_test_debug.dll')
if ($LASTEXITCODE -ne 0) { throw "Item height validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_start.py') --dll `
    (Join-Path $PSScriptRoot 'build\step_test.dll') `
    (Join-Path $PSScriptRoot 'build\step_test_debug.dll')
if ($LASTEXITCODE -ne 0) { throw "Lara startup validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_visual.py') --dll `
    (Join-Path $PSScriptRoot 'build\step_test.dll') `
    (Join-Path $PSScriptRoot 'build\step_test_debug.dll')
if ($LASTEXITCODE -ne 0) { throw "Visual asset validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_ground.py')
if ($LASTEXITCODE -ne 0) { throw "Ground collision/damping validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_air.py')
if ($LASTEXITCODE -ne 0) { throw "Airborne collision validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_fast_fall.py')
if ($LASTEXITCODE -ne 0) { throw "Fast-fall validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_forward_air.py')
if ($LASTEXITCODE -ne 0) { throw "Forward-air validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_standing_jump.py')
if ($LASTEXITCODE -ne 0) { throw "Standing-jump validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_directional_jump.py')
if ($LASTEXITCODE -ne 0) { throw "Directional jump validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_ledge.py')
if ($LASTEXITCODE -ne 0) { throw "Ledge grab/reach validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_hang.py')
if ($LASTEXITCODE -ne 0) { throw "Hanging/bounds validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_climb.py')
if ($LASTEXITCODE -ne 0) { throw "Climbing validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_water.py')
if ($LASTEXITCODE -ne 0) { throw "Water/vault validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_water_height.py')
if ($LASTEXITCODE -ne 0) { throw "Water height validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\check_dos_camera_smoothing.py')
if ($LASTEXITCODE -ne 0) { throw "DOS camera smoothing validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot 'tests\compare_camera_obstacles.py')
if ($LASTEXITCODE -ne 0) { throw "DOS camera obstacle/pitch validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_gym_audio.py')
if ($LASTEXITCODE -ne 0) { throw "Gym tutorial/completion validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tools\check_dos_static_render.py")
if ($LASTEXITCODE -ne 0) { throw "DOS static rendering checks failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_sound.py")
if ($LASTEXITCODE -ne 0) { throw "DOS sound parameter validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_slide.py")
if ($LASTEXITCODE -ne 0) { throw "DOS sliding validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_objects.py")
if ($LASTEXITCODE -ne 0) { throw "DOS door/switch validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot "tests\compare_door_contact.py")
if ($LASTEXITCODE -ne 0) { throw "DOS animated door contact validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot "tests\compare_switch_camera.py")
if ($LASTEXITCODE -ne 0) { throw "DOS switch camera validation failed: $LASTEXITCODE" }
& $Python (Join-Path $PSScriptRoot "tests\compare_dos_camera.py")
if ($LASTEXITCODE -ne 0) { throw "DOS full camera validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_hazards.py")
if ($LASTEXITCODE -ne 0) { throw "DOS hazard/projection validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_pistols.py")
if ($LASTEXITCODE -ne 0) { throw "pistols validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_creatures.py")
if ($LASTEXITCODE -ne 0) { throw "creatures validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_navigation.py")
if ($LASTEXITCODE -ne 0) { throw "navigation validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_creature_move.py")
if ($LASTEXITCODE -ne 0) { throw "creature_move validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_combat_camera.py")
if ($LASTEXITCODE -ne 0) { throw "combat_camera validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_combat.py")
if ($LASTEXITCODE -ne 0) { throw "combat validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_enemy_contact.py")
if ($LASTEXITCODE -ne 0) { throw "enemy_contact validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot "tests\compare_targeting.py")
if ($LASTEXITCODE -ne 0) { throw "Targeting validation failed: $LASTEXITCODE" }

& $Python (Join-Path $PSScriptRoot 'tests\compare_inventory.py')
if ($LASTEXITCODE -ne 0) { throw 'Inventory differential failed' }
& $Python (Join-Path $PSScriptRoot 'tests\compare_progression.py')
if ($LASTEXITCODE -ne 0) { throw 'Progression differential failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_text.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS text validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_ring.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS inventory ring validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_look.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS look validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_interface.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS interface validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_city.py')
if ($LASTEXITCODE -ne 0) { throw 'City DOS comparison failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_swan.py')
if ($LASTEXITCODE -ne 0) { throw 'Swan dive DOS comparison failed' }
& $Python (Join-Path $PSScriptRoot 'tests\compare_quest.py')
if ($LASTEXITCODE -ne 0) { throw 'Quest DOS comparison failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_city_next.py')
if ($LASTEXITCODE -ne 0) { throw 'Automatic look / pendulum DOS comparison failed' }
& $Python (Join-Path $PSScriptRoot 'tests\compare_frontend.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS front-end validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_dialog.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS dialog layout validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_shotgun.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS shotgun validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_shotgun_ray.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS shotgun ray validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_shotgun_targeting.py')
if ($LASTEXITCODE -ne 0) { throw 'DOS shotgun targeting validation failed' }

foreach ($comparison in @('compare_creatures.py','compare_navigation.py','compare_creature_move.py','compare_combat.py')) {
    & $Python (Join-Path $PSScriptRoot "tests\$comparison") LEVEL3A
    if ($LASTEXITCODE -ne 0) { throw "Valley DOS comparison failed: $comparison" }
}
& $Python (Join-Path $PSScriptRoot 'tests\compare_valley_effects.py')
if ($LASTEXITCODE -ne 0) { throw 'Valley stomp/camera DOS comparison failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_lighting.py') --dll (Join-Path $PSScriptRoot 'build\step_test.dll') (Join-Path $PSScriptRoot 'build\step_test_debug.dll')
if ($LASTEXITCODE -ne 0) { throw 'DOS model lighting validation failed' }

& $Python (Join-Path $PSScriptRoot 'tests\compare_peru.py')
if ($LASTEXITCODE -ne 0) { throw 'Peru controllers and room flips DOS comparison failed' }

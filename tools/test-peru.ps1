param([switch]$Debug)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
Set-Location $root
$env:ZIG_GLOBAL_CACHE_DIR=Join-Path $root 'work/zig-global-cache'
$env:ZIG_LOCAL_CACHE_DIR=Join-Path $root 'work/zig-local-cache'
$compiler=Join-Path $root 'work/toolchain/zig-x86_64-windows-0.15.2/zig.exe'
$sources=Get-ChildItem src -Filter '*.c' | Where-Object { $_.Name -notin @('preview.c','sound_win.c','movement_test.c') } | ForEach-Object FullName
$opt=if($Debug){'-O0'}else{'-O2'}
$out=if($Debug){'build/peru_test_debug.exe'}else{'build/peru_test.exe'}
& $compiler cc -target x86_64-windows-gnu -std=c11 $opt -g -Wall -Wextra -Werror -pedantic -I src @sources tests/peru_test.c -o $out
if($LASTEXITCODE){throw 'Peru test compilation failed'}
foreach($level in @('LEVEL3A','LEVEL3B')){
 & "./$out" "work/reference-assets/DATA/$level.PHD"
 if($LASTEXITCODE){throw "Peru integration failed: $level"}
}

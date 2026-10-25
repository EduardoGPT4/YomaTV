param([switch]$SkipTests)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
if(!$env:JAVA_HOME){throw 'JAVA_HOME debe apuntar a JDK 17.'}
$pcRoot=if(Test-Path YomaTVPC){'YomaTVPC'}else{'SeasonAV1'}
$python=if(Test-Path .venv/Scripts/python.exe){(Resolve-Path .venv/Scripts/python.exe).Path}else{'python'}
if(!$SkipTests){
    Push-Location $pcRoot
    try{& $python -m unittest discover -s tests; if($LASTEXITCODE){throw 'Fallaron las regresiones Windows.'}}finally{Pop-Location}
}
& $python "$pcRoot/build_exe.py"
if($LASTEXITCODE){throw 'No se compiló Windows.'}
Push-Location YomaTVAndroid
try{& ./tools/build.ps1 -Release; if($LASTEXITCODE){throw 'No se compiló Android.'}}finally{Pop-Location}
& $python release-tools/prepare_assets.py
if($LASTEXITCODE){throw 'No se pudieron preparar las publicaciones.'}

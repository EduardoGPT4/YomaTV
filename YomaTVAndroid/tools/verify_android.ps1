param([Parameter(Mandatory=$true)][string]$Device,[switch]$Live)
$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if($Device -notmatch '^[A-Za-z0-9:_.-]+$') { throw 'Identificador de dispositivo inválido.' }
$seasonSdk=if($env:ANDROID_HOME) {$env:ANDROID_HOME} else {Join-Path $env:LOCALAPPDATA 'Android/Sdk'}
$seasonAdb=Join-Path $seasonSdk 'platform-tools/adb.exe'
./gradlew.bat :engine:test :app:lintDebug :app:assembleDebug :app:assembleDebugAndroidTest --console=plain
if($LASTEXITCODE) { throw 'Falló la compilación o una comprobación local.' }
$seasonAapt=Get-ChildItem (Join-Path $seasonSdk 'build-tools/*/aapt.exe') | Sort-Object FullName -Descending | Select-Object -First 1
$seasonPackage=& $seasonAapt.FullName dump badging app/build/outputs/apk/debug/app-debug.apk
if(!($seasonPackage -match "package: name='app.seasonav1.mobile.qa'")) { throw 'El APK no es la variante aislada QA.' }
& $seasonAdb -s $Device install -r app/build/outputs/apk/debug/app-debug.apk
if($LASTEXITCODE) { throw 'Falló la instalación QA.' }
& $seasonAdb -s $Device install -r app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
if($LASTEXITCODE) { throw 'Falló la instalación de las pruebas.' }
$seasonArgs=@('-s',$Device,'shell','am','instrument','-w')
if($Live) {$seasonArgs+=@('-e','live','true')}
$seasonArgs+='app.seasonav1.mobile.qa.test/androidx.test.runner.AndroidJUnitRunner'
$seasonOutput=& $seasonAdb @seasonArgs
$seasonOutput | Set-Content verification/device-test-latest.log
$seasonOutput
if(($seasonOutput -join "`n") -notmatch 'OK \([0-9]+ tests\)' -or ($seasonOutput -match 'FAILURES|INSTRUMENTATION_FAILED')) { throw 'Una prueba Android falló. Consulta el registro.' }

param([switch]$Release)
$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if(!$env:JAVA_HOME -or !(Test-Path (Join-Path $env:JAVA_HOME 'bin/java.exe'))) { throw 'Configura JAVA_HOME con JDK 17 o superior.' }
$seasonSdk=if($env:ANDROID_HOME) {$env:ANDROID_HOME} else {Join-Path $env:LOCALAPPDATA 'Android/Sdk'}
if(!(Test-Path $seasonSdk)) { throw 'No se encontró Android SDK.' }
Set-Content -LiteralPath local.properties -Value ('sdk.dir='+($seasonSdk -replace '\\','/' -replace ':','\:'))
if($Release -and !(Test-Path private/seasonav1.jks)) {
    New-Item -ItemType Directory -Path private -Force | Out-Null
    $seasonPassword=[Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    Set-Content -LiteralPath private/signing.properties -Value ('password='+$seasonPassword)
    Set-Content -LiteralPath private/signing-pass.txt -Value $seasonPassword -NoNewline
    try {
        & (Join-Path $env:JAVA_HOME 'bin/keytool.exe') -genkeypair -alias seasonav1 -keystore private/seasonav1.jks -storetype PKCS12 -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=SeasonAV1 Personal' -storepass:file private/signing-pass.txt -keypass:file private/signing-pass.txt
        if($LASTEXITCODE) { throw 'No se pudo crear el certificado de distribución.' }
    } finally { Remove-Item -LiteralPath private/signing-pass.txt -ErrorAction SilentlyContinue; $seasonPassword=$null }
}
./gradlew.bat :engine:test :app:lintRelease :app:assembleRelease --console=plain
if($LASTEXITCODE) { throw 'La verificación o compilación de Android falló.' }
if($Release) {
    New-Item -ItemType Directory -Path artifacts -Force | Out-Null
    $yomaVersion=[regex]::Match((Get-Content app/build.gradle.kts -Raw),'versionName = "([0-9.]+)"').Groups[1].Value
    if(!$yomaVersion){throw 'No se pudo leer la versión Android.'}
    Copy-Item -LiteralPath app/build/outputs/apk/release/app-release.apk -Destination "artifacts/YomaTV-Android-$yomaVersion.apk"
    Get-FileHash -LiteralPath "artifacts/YomaTV-Android-$yomaVersion.apk" -Algorithm SHA256
}

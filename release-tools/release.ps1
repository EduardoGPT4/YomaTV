param([switch]$PublishPrepared)
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if(!$PublishPrepared){& ./release-tools/build_apps.ps1; if($LASTEXITCODE){throw 'Build failed'}}
$python=if(Test-Path .venv/Scripts/python.exe){(Resolve-Path .venv/Scripts/python.exe).Path}else{'python'}
& $python release-tools/publish_apps.py
if($LASTEXITCODE){throw 'Publication failed'}
& $python release-tools/verify_assets.py
if($LASTEXITCODE){throw 'Public download verification failed'}

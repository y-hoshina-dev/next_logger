$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

if (-not (Test-Path .venv\Scripts\python.exe)) {
  Write-Host 'No .venv found. Using system python.'
  $py = 'python'
} else {
  $py = '.venv\\Scripts\\python.exe'
}

# Force clean build to avoid stale cache artifacts.
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path next_logger.spec) { Remove-Item -Force next_logger.spec }

& $py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed.' }

& $py -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller install failed.' }

& $py -m PyInstaller --clean --noconfirm --onefile --windowed app.py --name next_logger
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed.' }

$artifact = Join-Path (Get-Location) 'dist\next_logger.exe'
if (-not (Test-Path $artifact)) { throw 'Build output not found: dist\\next_logger.exe' }

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$releaseDir = Join-Path (Get-Location) ("release\\" + $stamp)
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

$releaseExe = Join-Path $releaseDir 'next_logger.exe'
Copy-Item $artifact $releaseExe -Force

$hash = (Get-FileHash $releaseExe -Algorithm SHA256).Hash
$hashPath = Join-Path $releaseDir 'next_logger.sha256.txt'
$hash | Set-Content -Encoding ASCII $hashPath

Write-Host ("Build complete: " + $artifact)
Write-Host ("Release copy:  " + $releaseExe)
Write-Host ("SHA256:        " + $hash)

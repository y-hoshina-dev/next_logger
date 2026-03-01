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

$releaseRoot = Join-Path (Get-Location) 'release'
$latestDir = Join-Path $releaseRoot 'latest'
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

# Keep only one canonical release output.
Get-ChildItem -Path $releaseRoot -Directory -Force |
  Where-Object { $_.Name -ne 'latest' } |
  Remove-Item -Recurse -Force
if (Test-Path $latestDir) { Remove-Item -Recurse -Force $latestDir }
New-Item -ItemType Directory -Path $latestDir -Force | Out-Null

$releaseExe = Join-Path $latestDir 'next_logger.exe'
Move-Item -Path $artifact -Destination $releaseExe -Force

$hash = (Get-FileHash $releaseExe -Algorithm SHA256).Hash
$hashPath = Join-Path $latestDir 'next_logger.sha256.txt'
$hash | Set-Content -Encoding ASCII $hashPath

# Avoid duplicate EXE locations after build.
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path next_logger.spec) { Remove-Item -Force next_logger.spec }

Write-Host ("Build complete: " + $releaseExe)
Write-Host ("SHA256:        " + $hash)

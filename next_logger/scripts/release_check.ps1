$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

if (-not (Test-Path .venv\Scripts\python.exe)) {
  $py = 'python'
} else {
  $py = '.venv\\Scripts\\python.exe'
}

& $py -m unittest discover -s tests -p "test_*.py" -v
if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed.' }

& $py -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('next_logger').rglob('*.py')]; print('syntax-ok')"
if ($LASTEXITCODE -ne 0) { throw 'Syntax check failed.' }

Write-Host 'Release checks passed.'

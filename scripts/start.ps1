$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $ProjectRoot '.venv' }
$PythonExe = Join-Path $VenvDir 'Scripts/python.exe'

if (-not (Test-Path $PythonExe)) {
    python -m venv $VenvDir
    & "$VenvDir\Scripts\pip.exe" install --upgrade pip | Out-Null
    if (Test-Path (Join-Path $ProjectRoot 'requirements.txt')) {
        & "$VenvDir\Scripts\pip.exe" install -r (Join-Path $ProjectRoot 'requirements.txt')
    }
}

& "$VenvDir\Scripts\activate.ps1"
Set-Location $ProjectRoot
& $PythonExe (Join-Path $ProjectRoot 'main.py')

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $ProjectRoot '.venv' }

python -m venv $VenvDir
& "$VenvDir\Scripts\pip.exe" install --upgrade pip
$Requirements = Join-Path $ProjectRoot 'requirements.txt'
if (Test-Path $Requirements) {
    & "$VenvDir\Scripts\pip.exe" install -r $Requirements
}
else {
    & "$VenvDir\Scripts\pip.exe" install PySide6 pyperclip openai pynput
}

"Virtuelle Umgebung installiert. Aktiviere sie mit `& \"$VenvDir\\Scripts\\activate.ps1\"`."

# This Script is for installing dependencies for the Python Project
# Check if pip is installed
try {
    python -m pip --version | Out-Null
} catch {
    Write-Error "Error: pip is not installed. Please install Python and pip, then rerun this script."
    exit 1
}

# List of dependencies to install
$dependencies = @(
    "requests",
    "pyperclip",
    "PySide6"
)

foreach ($dep in $dependencies) {
    try {
        python -c "import $dep" 2>$null
        Write-Host "$dep is already installed"
    } catch {
        Write-Host "Installing $dep..."
        python -m pip install $dep
    }
}
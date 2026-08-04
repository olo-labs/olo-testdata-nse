[CmdletBinding()]
param(
    [switch]$Refresh,
    [switch]$VerifyOnly,
    [ValidateSet("local", "ci")]
    [string]$Profile = "local",
    [string]$Config = ""
)

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"

function Find-UsablePython {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"),
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    foreach ($name in @("py.exe", "python.exe", "python3.exe")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike "*WindowsApps*") { return $command.Source }
    }
    return $null
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $BasePython = Find-UsablePython
    if (-not $BasePython) {
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) {
            throw "Python 3.10+ is required and winget is unavailable. Install Python, then rerun run.bat."
        }
        Write-Host "Installing Python 3.12 for the current user..."
        & $winget.Source install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { throw "Python installation failed with exit code $LASTEXITCODE." }
        $BasePython = Find-UsablePython
        if (-not $BasePython) { throw "Python was installed but could not be located. Open a new terminal and rerun run.bat." }
    }
    Write-Host "Creating project-local Python environment..."
    & $BasePython -m venv (Join-Path $ProjectDir ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Unable to create the Python environment." }
}

$RequirementStamp = Join-Path $ProjectDir ".venv\.requirements-sha256"
$RequirementHash = (Get-FileHash -Algorithm SHA256 (Join-Path $ProjectDir "requirements.txt")).Hash
$InstalledHash = if (Test-Path $RequirementStamp) { (Get-Content $RequirementStamp -Raw).Trim() } else { "" }
if ($InstalledHash -ne $RequirementHash) {
    Write-Host "Installing project dependencies (including DuckDB)..."
    & $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $ProjectDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    Set-Content -LiteralPath $RequirementStamp -Value $RequirementHash -NoNewline
}

$Arguments = @((Join-Path $ProjectDir "fast_build_database.py"))
$Arguments += @("--profile", $Profile)
if ($Config) { $Arguments += @("--config", $Config) }
if ($Refresh) { $Arguments += "--refresh" }
if ($VerifyOnly) { $Arguments += "--verify-only" }
$env:PYTHONUNBUFFERED = "1"
& $VenvPython @Arguments
exit $LASTEXITCODE

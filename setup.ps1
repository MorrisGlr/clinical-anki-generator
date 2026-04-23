# setup.ps1 — HEART first-time setup for Windows 10+
# Run from the project root in PowerShell:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # one-time, if needed
#   .\setup.ps1

$ErrorActionPreference = "Stop"

function ok   { param($msg) Write-Host "  " -NoNewline; Write-Host "[OK] " -ForegroundColor Green -NoNewline; Write-Host $msg }
function fail { param($msg) Write-Host "  " -NoNewline; Write-Host "[X]  " -ForegroundColor Red   -NoNewline; Write-Host $msg }
function info { param($msg) Write-Host "  " -NoNewline; Write-Host " ->  " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function hr   { Write-Host ("─" * 42) }

Write-Host ""
Write-Host "HEART Setup — Windows" -ForegroundColor White
hr

# ── 1. Windows check ──────────────────────────────────────────────────────────
if ($IsWindows -eq $false) {
    fail "This script is for Windows only."
    info "For macOS or Linux setup, run: ./setup.sh"
    exit 1
}
ok "Windows detected"

# ── 2. Python 3.10+ check ─────────────────────────────────────────────────────
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd -c "import sys; print(sys.version_info[:2])" 2>$null
        $major   = & $cmd -c "import sys; print(sys.version_info[0])"  2>$null
        $minor   = & $cmd -c "import sys; print(sys.version_info[1])"  2>$null
        if ($major -ge 3 -and $minor -ge 10) {
            $pythonCmd = $cmd
            break
        }
    } catch { }
}

if (-not $pythonCmd) {
    fail "Python 3.10 or later not found."
    Write-Host ""
    info "Install Python with winget (recommended), then re-run this script:"
    Write-Host ""
    Write-Host "      winget install Python.Python.3.12" -ForegroundColor Cyan
    Write-Host ""
    info "Or download from: https://www.python.org/downloads/"
    info "Check 'Add Python to PATH' during installation."
    Write-Host ""
    exit 1
}

$pythonVersion = & $pythonCmd -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
ok "Python $pythonVersion found ($pythonCmd)"

# ── 3. Virtual environment ────────────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    info "Creating virtual environment in .venv ..."
    & $pythonCmd -m venv .venv
    ok "Virtual environment created"
} else {
    ok "Virtual environment already exists"
}

# Activate
& .\.venv\Scripts\Activate.ps1
ok "Virtual environment activated"

# ── 4. Install HEART ──────────────────────────────────────────────────────────
info "Installing HEART and dependencies (this may take a minute) ..."
pip install --quiet -e .
ok "HEART installed"

# ── 5. OpenAI API key ─────────────────────────────────────────────────────────
hr
Write-Host ""
Write-Host "OpenAI API Key Setup" -ForegroundColor White
Write-Host ""

$writeKey = $true

if ((Test-Path ".env") -and (Select-String -Path ".env" -Pattern "OPENAI_API_KEY" -Quiet)) {
    Write-Host "  A .env file already contains an OPENAI_API_KEY."
    $overwrite = Read-Host "  Overwrite it? [y/N]"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        ok "Keeping existing API key"
        $writeKey = $false
    }
}

if ($writeKey) {
    Write-Host ""
    Write-Host "  Your OpenAI API key starts with 'sk-'."
    Write-Host "  Don't have one yet? See SETUP.md -> 'Get your OpenAI API key'."
    Write-Host ""
    $apiKey = Read-Host "  Paste your OpenAI API key and press Enter"

    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        fail "No key entered. You can add it later by editing the .env file:"
        Write-Host "      Add a line:  OPENAI_API_KEY=sk-your-key-here"
    } else {
        if (Test-Path ".env") {
            # Remove any existing OPENAI_API_KEY line
            $envContent = Get-Content ".env" | Where-Object { $_ -notmatch "^OPENAI_API_KEY=" }
            Set-Content ".env" $envContent
        }
        Add-Content ".env" "OPENAI_API_KEY=$apiKey"
        ok "API key saved to .env"
    }
}

# ── 6. Verify installation ────────────────────────────────────────────────────
hr
Write-Host ""
info "Verifying installation ..."
try {
    & heart --help | Out-Null
    ok "heart CLI is working"
} catch {
    fail "heart --help failed. Try running: pip install -e ."
    exit 1
}

# ── 7. Done ───────────────────────────────────────────────────────────────────
Write-Host ""
hr
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:"
Write-Host ""
Write-Host "  1. Activate your environment before each session:"
Write-Host "        .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "  2. Verify everything is ready:"
Write-Host "        heart check"
Write-Host ""
Write-Host "  3. Place your saved HTML files in the html_dump\ folder, then run:"
Write-Host "        heart --platform uworld"
Write-Host ""
Write-Host "  For full instructions, see SETUP.md"
Write-Host ""

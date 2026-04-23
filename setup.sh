#!/usr/bin/env bash
# setup.sh — HEART first-time setup for macOS and Linux (Ubuntu 22.04+)
# Run from the project root: ./setup.sh

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
RESET="\033[0m"

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; }
fail() { echo -e "  ${RED}✗${RESET}  $*"; }
info() { echo -e "  ${YELLOW}→${RESET}  $*"; }
hr()   { echo "──────────────────────────────────────────"; }

echo ""
echo -e "${BOLD}HEART Setup${RESET}"
hr

# ── 1. Platform check ─────────────────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
  Darwin)
    PLATFORM="macos"
    ok "macOS detected"
    ;;
  Linux)
    PLATFORM="linux"
    ok "Linux detected"
    ;;
  *)
    fail "Unsupported platform: $OS"
    info "For Windows setup, run setup.ps1 in PowerShell. See SETUP.md for instructions."
    exit 1
    ;;
esac

# ── 2. Python 3.10+ check ─────────────────────────────────────────────────────
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        major=$("$cmd" -c 'import sys; print(sys.version_info[0])')
        minor=$("$cmd" -c 'import sys; print(sys.version_info[1])')
        if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    fail "Python 3.10 or later not found."
    echo ""
    if [[ "$PLATFORM" == "macos" ]]; then
        if command -v brew &>/dev/null; then
            info "Homebrew is installed. Run this command to install Python, then re-run setup.sh:"
            echo ""
            echo "      brew install python@3.12"
            echo ""
        else
            info "Install Python from the official site, then re-run setup.sh:"
            echo ""
            echo "      https://www.python.org/downloads/"
            echo ""
            info "Download the macOS installer package (.pkg) and follow the prompts."
            echo ""
        fi
    else
        info "Install Python with apt, then re-run setup.sh:"
        echo ""
        echo "      sudo apt update && sudo apt install python3.12 python3.12-venv"
        echo ""
        info "Or install from the official site: https://www.python.org/downloads/"
        echo ""
    fi
    exit 1
fi

PYTHON_VERSION=$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
ok "Python $PYTHON_VERSION found ($PYTHON)"

# ── 3. Virtual environment ────────────────────────────────────────────────────
if [[ ! -d ".venv" ]]; then
    info "Creating virtual environment in .venv ..."
    "$PYTHON" -m venv .venv
    ok "Virtual environment created"
else
    ok "Virtual environment already exists"
fi

# Activate
# shellcheck source=/dev/null
source .venv/bin/activate
ok "Virtual environment activated"

# ── 4. Install HEART ──────────────────────────────────────────────────────────
info "Installing HEART and dependencies (this may take a minute) ..."
pip install --quiet -e .
ok "HEART installed"

# ── 5. OpenAI API key ─────────────────────────────────────────────────────────
hr
echo ""
echo -e "${BOLD}OpenAI API Key Setup${RESET}"
echo ""

WRITE_KEY=true

if [[ -f ".env" ]] && grep -q "OPENAI_API_KEY" .env 2>/dev/null; then
    echo -e "  A .env file already contains an OPENAI_API_KEY."
    printf "  Overwrite it? [y/N] "
    read -r OVERWRITE
    if [[ "$OVERWRITE" != "y" && "$OVERWRITE" != "Y" ]]; then
        ok "Keeping existing API key"
        WRITE_KEY=false
    fi
fi

if [[ "$WRITE_KEY" == true ]]; then
    echo ""
    echo "  Your OpenAI API key starts with 'sk-'."
    echo "  Don't have one yet? See SETUP.md → 'Get your OpenAI API key'."
    echo ""
    printf "  Paste your OpenAI API key and press Enter: "
    read -r API_KEY

    if [[ -z "$API_KEY" ]]; then
        fail "No key entered. You can add it later by editing the .env file:"
        echo "      echo 'OPENAI_API_KEY=sk-your-key-here' > .env"
    else
        if [[ -f ".env" ]]; then
            grep -v "^OPENAI_API_KEY=" .env > .env.tmp && mv .env.tmp .env
        fi
        echo "OPENAI_API_KEY=$API_KEY" >> .env
        ok "API key saved to .env"
    fi
fi

# ── 6. Verify installation ────────────────────────────────────────────────────
hr
echo ""
info "Verifying installation ..."
if heart --help &>/dev/null; then
    ok "heart CLI is working"
else
    fail "heart --help failed. Try running: pip install -e ."
    exit 1
fi

# ── 7. Done ───────────────────────────────────────────────────────────────────
echo ""
hr
echo ""
echo -e "${BOLD}${GREEN}Setup complete!${RESET}"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Activate your environment before each session:"
echo "        source .venv/bin/activate"
echo ""
echo "  2. Verify everything is ready:"
echo "        heart check"
echo ""
echo "  3. Place your saved HTML files in the html_dump/ folder, then run:"
echo "        heart --platform uworld"
echo ""
echo "  For full instructions, see SETUP.md"
echo ""

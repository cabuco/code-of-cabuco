#!/usr/bin/env bash
set -euo pipefail

LOG="[pwsh+exo-setup]"
log() { echo "$LOG $*"; }
fail() { echo "$LOG ERROR: $*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "This script must be run on macOS."

# --- Sudo warm-up (needed for pkg install)
if ! sudo -n true 2>/dev/null; then
  log "Sudo is required for installation steps."
  sudo -v
fi

# --- Ensure Xcode Command Line Tools (CLT)
if ! xcode-select -p >/dev/null 2>&1; then
  log "Xcode Command Line Tools not found. Launching installer prompt..."
  xcode-select --install || true
  log "Waiting for Command Line Tools installation to complete..."
  until xcode-select -p >/dev/null 2>&1; do
    sleep 20
  done
  log "Xcode Command Line Tools installed."
else
  log "Xcode Command Line Tools already present."
fi

# --- Install PowerShell (official pkg) if missing
if command -v pwsh >/dev/null 2>&1; then
  log "PowerShell already installed: $(pwsh --version 2>/dev/null || true)"
else
  ARCH="$(uname -m)"
  if [[ "$ARCH" == "arm64" ]]; then
    PS_ARCH="arm64"
  elif [[ "$ARCH" == "x86_64" ]]; then
    PS_ARCH="x64"
  else
    fail "Unsupported architecture: $ARCH"
  fi
  log "Detected architecture: $ARCH ($PS_ARCH)"

  LATEST_TAG="$(curl -fsSL -o /dev/null -w '%{url_effective}' https://github.com/PowerShell/PowerShell/releases/latest | awk -F/ '{print $NF}')"
  [[ -n "$LATEST_TAG" ]] || fail "Could not determine latest PowerShell release tag."
  PS_VERSION="${LATEST_TAG#v}"

  PKG_NAME="powershell-${PS_VERSION}-osx-${PS_ARCH}.pkg"
  DOWNLOAD_URL="https://github.com/PowerShell/PowerShell/releases/download/${LATEST_TAG}/${PKG_NAME}"
  DOWNLOAD_PATH="$HOME/Downloads/$PKG_NAME"

  log "Downloading PowerShell ${PS_VERSION}..."
  curl -fL "$DOWNLOAD_URL" -o "$DOWNLOAD_PATH"

  log "Removing Gatekeeper quarantine attribute on downloaded pkg..."
  sudo xattr -rd com.apple.quarantine "$DOWNLOAD_PATH"

  log "Installing PowerShell pkg..."
  sudo installer -pkg "$DOWNLOAD_PATH" -target /

  command -v pwsh >/dev/null 2>&1 || fail "PowerShell install completed but pwsh is not on PATH."
  log "PowerShell installed successfully: $(pwsh --version 2>/dev/null || true)"
fi

# --- Create a temp PowerShell bootstrap file to avoid quoting issues
TMP_PS="$(mktemp -t exo_bootstrap_XXXXXX.ps1)"

cat > "$TMP_PS" <<'PS1'
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== EXO bootstrap (PowerShell) ==="
Write-Host ""

# Requested by you (non-fatal if blocked in some environments)
try { Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force } catch {}

# Install EXO module (PowerShell Gallery) (CurrentUser)
# Microsoft guidance is Install-Module -Name ExchangeOnlineManagement (often with -Scope CurrentUser) [6](https://learn.microsoft.com/en-us/powershell/exchange/exchange-online-powershell-v2?view=exchange-ps)
Write-Host "Installing ExchangeOnlineManagement module (CurrentUser)..."
Install-Module -Name ExchangeOnlineManagement -Scope CurrentUser -Force -AllowClobber

Write-Host "Importing ExchangeOnlineManagement module..."
Import-Module ExchangeOnlineManagement

Write-Host ""
Write-Host "EXO module is installed."
Write-Host "Now connect to Azure VPN (if you are not connected already)."
Write-Host "When Azure VPN is connected, type YES to continue."
$vpnConfirm = Read-Host "Azure VPN connected? (type YES to continue)"
if ($vpnConfirm -ne "YES") {
  Write-Host "Stopping here. Re-run after connecting to Azure VPN."
  exit 1
}

# No default UPN: user must supply it (your request)
Write-Host ""
Write-Host "Enter your SC-ALT account email address (required)."
do {
  $scAltUpn = Read-Host "SC-ALT UPN"
} until ($scAltUpn -match '^[^@\s]+@[^@\s]+\.[^@\s]+$')

Write-Host ""
Write-Host "Connecting to Exchange Online..."

function Try-ConnectExo {
  param([string]$Upn)

  try {
    # Standard connect syntax [4](https://learn.microsoft.com/en-us/powershell/exchange/connect-to-exchange-online-powershell?view=exchange-ps)
    Connect-ExchangeOnline -UserPrincipalName $Upn -ShowBanner:$false
    return $true
  } catch {
    $msg = $_.Exception.ToString()

    # macOS 26 MSAL default browser path can throw PlatformNotSupportedException / StartDefaultOsBrowserAsync [1](https://github.com/unoplatform/uno/issues/22023)
    if ($msg -match "PlatformNotSupportedException" -or $msg -match "StartDefaultOsBrowserAsync" -or $msg -match "Error Acquiring Token") {
      Write-Host ""
      Write-Host "Detected macOS browser auth not supported on this OS. Retrying with device code auth (-Device)..."
      # Field workaround: Connect-ExchangeOnline -Device works when normal interactive fails [2](https://github.com/PowerShell/PowerShell/issues/25125)
      Connect-ExchangeOnline -UserPrincipalName $Upn -Device -ShowBanner:$false
      return $true
    }

    throw
  }
}

$connected = $false

try {
  $connected = Try-ConnectExo -Upn $scAltUpn
} catch {
  Write-Host ""
  Write-Host "Initial connect attempt failed."
  Write-Host $_.Exception.Message

  Write-Host ""
  Write-Host "Attempting a self-correcting fallback: reinstalling a lower ExchangeOnlineManagement version and retrying."
  Write-Host "Note: compatibility issues have been observed on macOS 26.3 with some newer versions. [3](https://www.powershellgallery.com/packages/ExoAliasManagement/0.0.9)"

  try {
    # Remove all versions, then install a lower baseline version.
    Get-Module ExchangeOnlineManagement -ErrorAction SilentlyContinue | Remove-Module -Force -ErrorAction SilentlyContinue
    Get-InstalledModule ExchangeOnlineManagement -ErrorAction SilentlyContinue | Out-Null
  } catch {}

  try { Uninstall-Module -Name ExchangeOnlineManagement -AllVersions -Force -ErrorAction SilentlyContinue } catch {}

  # Baseline version chosen based on observed macOS 26.3 compatibility notes [3](https://www.powershellgallery.com/packages/ExoAliasManagement/0.0.9)
  Install-Module -Name ExchangeOnlineManagement -RequiredVersion 3.6.0 -Scope CurrentUser -Force -AllowClobber
  Import-Module ExchangeOnlineManagement -Force

  # Retry with device auth first to avoid browser auth on macOS 26 [1](https://github.com/unoplatform/uno/issues/22023)[2](https://github.com/PowerShell/PowerShell/issues/25125)
  Connect-ExchangeOnline -UserPrincipalName $scAltUpn -Device -ShowBanner:$false
  $connected = $true
}

if (-not $connected) {
  throw "Unable to connect to Exchange Online."
}

Write-Host ""
Write-Host "Connected. Running a test command to confirm it's working..."

# Simple verification command commonly used after connect (may require RBAC permissions) [5](https://www.commandinline.com/powershell/how-to-connect-to-exchange-online-via-powershell/)
try {
  Get-EXOMailbox -ResultSize 1 | Select-Object DisplayName, PrimarySmtpAddress | Format-Table -AutoSize
  Write-Host ""
  Write-Host "Smoke test succeeded."
} catch {
  Write-Host ""
  Write-Host "Connected, but the test cmdlet failed (could be permission/RBAC)."
  Write-Host $_.Exception.Message
  throw
}

Write-Host ""
Write-Host "All done."
PS1

# --- Run the PowerShell bootstrap
pwsh -NoLogo -NoProfile -File "$TMP_PS"

# --- Cleanup
rm -f "$TMP_PS"
log "Finished."
log "When done later: pwsh then Disconnect-ExchangeOnline"
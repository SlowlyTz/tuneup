#!/usr/bin/env bash
# Tuneup installer – the settings app Omarchy is missing.
#
#   curl -fsSL https://raw.githubusercontent.com/SlowlyTz/tuneup/master/install.sh | bash
#   git clone https://github.com/SlowlyTz/tuneup.git && ./tuneup/install.sh
#
# From a git checkout it installs that checkout in place; piped from curl it
# clones to ~/.local/share/tuneup (running it again there updates it).
#
#   --yes       take the default answers, ask nothing
#   --no-deps   install no packages (and skip the camera, which needs some)
#   --update    what the app's update button runs: no questions, the earlier
#               answers, a password only (pkexec) if new packages are missing
#   --dry-run   print every action instead of doing it
set -euo pipefail

CLONE_URL="https://github.com/SlowlyTz/tuneup.git"
YES=0 NO_DEPS=0 UPDATE=0 DRY=0
ARGS=("$@")
for arg in "$@"; do
  case "$arg" in
    -y|--yes) YES=1 ;;
    --no-deps) NO_DEPS=1 ;;
    --update) UPDATE=1 YES=1 ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,14p' "${BASH_SOURCE[0]:-/dev/null}" 2>/dev/null | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'Unknown option: %s (see --help)\n' "$arg" >&2; exit 2 ;;
  esac
done

# --- output -----------------------------------------------------------------------------
if [ -t 1 ]; then
  BOLD=$'\e[1m' DIM=$'\e[2m' RED=$'\e[31m' GREEN=$'\e[32m' YELLOW=$'\e[33m' BLUE=$'\e[34m' RESET=$'\e[0m'
else
  BOLD="" DIM="" RED="" GREEN="" YELLOW="" BLUE="" RESET=""
fi
step() { printf '\n%s==>%s %s%s%s\n' "$BLUE" "$RESET" "$BOLD" "$*" "$RESET"; }
ok() { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$*"; }
note() { printf '  %s!%s %s\n' "$YELLOW" "$RESET" "$*"; }
fail() { printf '\n%s✗ %s%s\n' "$RED" "$*" "$RESET" >&2; exit 1; }
# Every change goes through run: --dry-run only prints it.
run() {
  if [ "$DRY" = 1 ]; then printf '  %s[dry-run]%s %s\n' "$DIM" "$RESET" "$*"; else "$@"; fi
}

# --- where Tuneup lives -------------------------------------------------------------------
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CLONE="$DATA_HOME/tuneup"
HERE=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "$HERE" ] && [ -f "$HERE/hypr_screens/cli.py" ] && [ -d "$HERE/.git" ]; then
  REPO="$HERE"
else
  # Piped from curl (or a copy of the script): get the code first.
  command -v git >/dev/null || fail "git is needed to download Tuneup: sudo pacman -S git"
  step "Downloading Tuneup to $CLONE"
  if [ -d "$CLONE/.git" ]; then
    run git -C "$CLONE" pull --ff-only --quiet
  else
    run mkdir -p "$DATA_HOME"
    run git clone --quiet "$CLONE_URL" "$CLONE"
  fi
  if [ ! -f "$CLONE/install.sh" ]; then
    note "the rest runs from $CLONE/install.sh once it is downloaded"
    exit 0
  fi
  exec bash "$CLONE/install.sh" "${ARGS[@]}"
fi
TUNEUP=(python3 "$REPO/tuneup")
helper() { "${TUNEUP[@]}" installer "$@"; }

# --- 1. checks ------------------------------------------------------------------------------
step "Checking the system"
command -v pacman >/dev/null || fail "Tuneup needs an Arch-based system (pacman)."
command -v python3 >/dev/null || fail "Python 3 is missing: sudo pacman -S python"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' ||
  fail "Tuneup needs Python 3.10 or newer (this is $(python3 -V 2>&1))."
command -v hyprctl >/dev/null || fail "Hyprland is missing. Tuneup is made for Hyprland ≥ 0.56."
HYPR_VERSION="$(hyprctl version -j 2>/dev/null | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("version", ""))
except Exception: print("")' || true)"
[ -n "$HYPR_VERSION" ] || fail "Hyprland is not running: run the installer inside your Hyprland session."
python3 - "$HYPR_VERSION" <<'PY' || fail "Tuneup needs Hyprland 0.56 or newer (this is $HYPR_VERSION)."
import re, sys
sys.exit(tuple(int(n) for n in re.findall(r"\d+", sys.argv[1])[:2]) < (0, 56))
PY
HYPR_LUA="${XDG_CONFIG_HOME:-$HOME/.config}/hypr/hyprland.lua"
[ -f "$HYPR_LUA" ] || fail "Tuneup needs Hyprland's Lua config ($HYPR_LUA)."
ok "Hyprland $HYPR_VERSION with a Lua config, Python $(python3 -c 'import platform; print(platform.python_version())')"
if command -v omarchy >/dev/null || [ -d "$DATA_HOME/omarchy" ]; then
  ok "Omarchy"
else
  note "Omarchy not found: Tuneup works, but without the window list and the bar widgets."
fi
command -v git >/dev/null || note "git is missing: it comes with the packages (updates need it)."

# --- 2. questions first, so the password is asked once ----------------------------------------
declare -A REMEMBERED=()
while IFS='=' read -r key value; do
  [ -n "$key" ] && REMEMBERED[$key]="$value"
done < <(helper choices)
GALAXY_BOOK=0
helper galaxy-book && GALAXY_BOOK=1

ask() {  # ask "question" default(y|n) -> 1 or 0; --yes and no terminal take the default
  local question="$1" default="$2" answer=""
  if [ "$YES" = 0 ] && { true </dev/tty; } 2>/dev/null; then
    local hint="[y/N]"; [ "$default" = y ] && hint="[Y/n]"
    printf '  %s %s ' "$question" "$hint" >/dev/tty
    read -r answer </dev/tty || answer=""
  fi
  answer="${answer:-$default}"
  case "$answer" in [yYjJ]*) echo 1 ;; *) echo 0 ;; esac
}
had() {  # had key -> 1 when that part is there already (an earlier install)
  case "$1" in
    camera) helper set-up camera >/dev/null 2>&1 && echo 1 || echo 0 ;;
    cava) command -v cava >/dev/null && echo 1 || echo 0 ;;
    galaxy_book) helper set-up galaxy-book >/dev/null 2>&1 && echo 1 || echo 0 ;;
  esac
}
choice() {  # choice key "question" default: the earlier answer, else what is there, else the default
  local before="${REMEMBERED[$1]:-}"
  [ -n "$before" ] || { [ "$(had "$1")" = 1 ] && before=1; }
  if [ "$UPDATE" = 1 ]; then echo "${before:-0}"; return; fi
  local default="$3"
  [ -n "$before" ] && { [ "$before" = 1 ] && default=y || default=n; }
  ask "$2" "$default"
}
if [ "$UPDATE" = 0 ]; then step "A few questions"; else step "Your earlier choices"; fi
WANT_CAMERA="$(choice camera "Camera: a rotated virtual camera for apps? (v4l2loopback)" n)"
WANT_CAVA="$(choice cava "Visualizer for the desktop widgets? (cava)" n)"
WANT_GALAXY=0
if [ "$GALAXY_BOOK" = 1 ]; then
  WANT_GALAXY="$(choice galaxy_book "Set up Galaxy Book support (charge limit, performance modes, keyboard light)?" y)"
fi
yes_no() { [ "$1" = 1 ] && echo yes || echo no; }
SUMMARY="camera: $(yes_no "$WANT_CAMERA") · visualizer: $(yes_no "$WANT_CAVA")"
[ "$GALAXY_BOOK" = 1 ] && SUMMARY="$SUMMARY · Galaxy Book: $(yes_no "$WANT_GALAXY")"
ok "$SUMMARY"

# --- 3. packages and the root setups, in one go ------------------------------------------------
WANTED=()
[ "$WANT_CAMERA" = 1 ] && WANTED+=(camera)
[ "$WANT_CAVA" = 1 ] && WANTED+=(cava)
mapfile -t PACKAGES < <(helper packages "${WANTED[@]}")
MISSING=()
if [ "$NO_DEPS" = 0 ]; then
  mapfile -t MISSING < <(pacman -T "${PACKAGES[@]}" || true)
fi
ROOT_SETUPS=()
if [ "$WANT_CAMERA" = 1 ] && ! helper set-up camera; then
  if [ "$NO_DEPS" = 1 ]; then note "--no-deps: the camera needs packages, so it is not set up"; else ROOT_SETUPS+=(camera); fi
fi
if [ "$WANT_GALAXY" = 1 ] && ! helper set-up galaxy-book; then ROOT_SETUPS+=(galaxy-book); fi

if [ "${#MISSING[@]}" -gt 0 ] || [ "${#ROOT_SETUPS[@]}" -gt 0 ]; then
  step "Packages and system setup"
  [ "${#MISSING[@]}" -gt 0 ] && printf '  Tuneup now installs its dependencies from the official Arch repositories\n  (pacman, nothing from the AUR): %s\n' "${MISSING[*]}"
  for what in "${ROOT_SETUPS[@]}"; do printf '  One-time setup as root: %s\n' "$what"; done
  ROOT_SCRIPT="$(mktemp "${TMPDIR:-/tmp}/tuneup-root.XXXXXX.sh")"
  trap 'rm -f "$ROOT_SCRIPT"' EXIT
  {
    echo "set -e"
    [ "${#MISSING[@]}" -gt 0 ] && echo "pacman -S --needed --noconfirm ${MISSING[*]}"
    for what in "${ROOT_SETUPS[@]}"; do helper root-script "$what"; done
  } >"$ROOT_SCRIPT"
  if [ "$DRY" = 1 ]; then sed 's/^/    | /' "$ROOT_SCRIPT"; fi
  if [ "$UPDATE" = 1 ]; then
    printf '  A password dialog asks for your password once.\n'
    run pkexec /bin/sh "$ROOT_SCRIPT" || fail "The system setup did not run (password dialog cancelled?)."
  else
    printf '  sudo asks for your password once.\n'
    run sudo /bin/sh "$ROOT_SCRIPT" || fail "The system setup failed; nothing else was changed. Run the installer again."
  fi
  ok "done"
elif [ "$NO_DEPS" = 1 ]; then
  note "--no-deps: no packages installed"
fi

# --- 4. into Hyprland and Omarchy, as you ------------------------------------------------------
step "Setting up Tuneup"
run "${TUNEUP[@]}" installer remember "camera=$WANT_CAMERA" "cava=$WANT_CAVA" "galaxy_book=$WANT_GALAXY"
run "${TUNEUP[@]}" setup
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) note "~/.local/bin is not on your PATH: add it to use the tuneup command in a terminal" ;;
esac

# --- 5. start it ---------------------------------------------------------------------------------
step "Starting Tuneup"
run "${TUNEUP[@]}" restart --open
VERSION="$(helper version)"
if [ "$UPDATE" = 1 ]; then
  printf '\n%s✓ Tuneup %s is up to date.%s\n' "$GREEN" "$VERSION" "$RESET"
else
  printf '\n%s✓ Tuneup %s is installed.%s It lives in the tray now (the icon in the bar);\n' "$GREEN" "$VERSION" "$RESET"
  printf '  open it from there, from the app launcher, or with: tuneup settings\n'
fi

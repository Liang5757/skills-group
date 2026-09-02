#!/usr/bin/env bash

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="$REPO_ROOT/install.sh"
SANDBOX="$(mktemp -d)"
USER_DIR="$SANDBOX/User Home 测试"
CACHE_DIR="$SANDBOX/Cache Root"
FIXTURE_DIR="$SANDBOX/fixture"
INVALID_DIR="$SANDBOX/invalid"
PASS=0
FAIL=0

cleanup() {
  rm -rf "$SANDBOX"
}
trap cleanup EXIT HUP INT TERM

pass() {
  PASS=$((PASS + 1))
  printf '  \033[0;32m✓\033[0m %s\n' "$1"
}

fail() {
  FAIL=$((FAIL + 1))
  printf '  \033[0;31m✗\033[0m %s\n' "$1" >&2
}

assert_true() {
  label="$1"
  shift
  if "$@"; then pass "$label"; else fail "$label"; fi
}

assert_eq() {
  label="$1"
  expected="$2"
  actual="$3"
  if [ "$expected" = "$actual" ]; then
    pass "$label"
  else
    fail "$label (expected '$expected', got '$actual')"
  fi
}

run_installer() {
  source_root="$1"
  remote_sha="$2"
  shift 2
  SKILLS_GROUP_USER_HOME="$USER_DIR" \
  SKILLS_GROUP_HOME="$CACHE_DIR" \
  SKILLS_GROUP_SOURCE_ROOT="$source_root" \
  SKILLS_GROUP_REMOTE_SHA="$remote_sha" \
  SKILLS_GROUP_DISABLE_COMMAND_DETECTION=1 \
    bash "$INSTALLER" "$@"
}

mkdir -p "$USER_DIR/.codex"

printf 'Read-only status\n'
run_installer "$REPO_ROOT" "version-one" --status >/dev/null
assert_true "status does not create the cache" test ! -e "$CACHE_DIR"

printf 'Initial install and detection\n'
run_installer "$REPO_ROOT" "version-one" >/dev/null
codex_dir="$USER_DIR/.agents/skills"
assert_eq "all eight skills are linked" "8" "$(find "$codex_dir" -mindepth 1 -maxdepth 1 -type l | wc -l | tr -d ' ')"
assert_true "skill link resolves through a path containing spaces" test -f "$codex_dir/changelog-generator/SKILL.md"
assert_true "undetected Claude is not modified" test ! -d "$USER_DIR/.claude/skills"

printf 'Idempotency and conflict backup\n'
run_installer "$REPO_ROOT" "version-one" >/dev/null
assert_true "idempotent reinstall creates no backup" test ! -d "$CACHE_DIR/backups"
mkdir -p "$USER_DIR/.claude/skills/changelog-generator"
printf 'user-owned\n' > "$USER_DIR/.claude/skills/changelog-generator/user.txt"
run_installer "$REPO_ROOT" "version-one" --agent claude --skill changelog-generator >/dev/null
assert_true "conflicting directory is replaced by a managed link" test -L "$USER_DIR/.claude/skills/changelog-generator"
backup_file="$(find "$CACHE_DIR/backups" -type f -name user.txt | head -n 1)"
assert_true "conflicting directory content is backed up" test -f "$backup_file"

printf 'Version checks\n'
run_installer "$REPO_ROOT" "version-one" --check >/dev/null
assert_eq "current version returns zero" "0" "$?"
set +e
run_installer "$REPO_ROOT" "version-two" --check >/dev/null
outdated_rc=$?
set -e
assert_eq "available update returns ten" "10" "$outdated_rc"

printf 'Update and stale-link cleanup\n'
mkdir -p "$FIXTURE_DIR"
cp -R "$REPO_ROOT/skills" "$FIXTURE_DIR/skills"
rm -rf "$FIXTURE_DIR/skills/video-downloader"
ln -s "$SANDBOX/external-source" "$codex_dir/external-skill"
mkdir -p "$SANDBOX/external-source"
run_installer "$FIXTURE_DIR" "version-two" >/dev/null
assert_true "removed upstream skill link is cleaned" test ! -e "$codex_dir/video-downloader"
assert_true "external symlink is preserved" test -L "$codex_dir/external-skill"
assert_eq "new version is recorded" "version-two" "$(tr -d '[:space:]' < "$CACHE_DIR/version")"

printf 'Invalid update rollback\n'
mkdir -p "$INVALID_DIR/skills/bad-skill"
printf '%s\n' '---' 'name: other-name' 'description: invalid fixture' '---' > "$INVALID_DIR/skills/bad-skill/SKILL.md"
run_installer "$INVALID_DIR" "version-three" --force >/dev/null 2>&1
assert_eq "invalid update keeps previous version" "version-two" "$(tr -d '[:space:]' < "$CACHE_DIR/version")"
assert_true "previous cache remains usable" test -f "$codex_dir/changelog-generator/SKILL.md"

printf 'Offline fallback and safe uninstall\n'
SKILLS_GROUP_USER_HOME="$USER_DIR" \
SKILLS_GROUP_HOME="$CACHE_DIR" \
SKILLS_GROUP_API_URL="http://127.0.0.1:9/unavailable" \
SKILLS_GROUP_DISABLE_COMMAND_DETECTION=1 \
  bash "$INSTALLER" --agent codex >/dev/null 2>&1
assert_true "offline install keeps cached links usable" test -f "$codex_dir/changelog-generator/SKILL.md"
run_installer "$FIXTURE_DIR" "version-two" --uninstall >/dev/null
assert_eq "uninstall removes managed links" "0" "$(find "$codex_dir" -mindepth 1 -maxdepth 1 -type l ! -name external-skill | wc -l | tr -d ' ')"
assert_true "uninstall preserves external symlink" test -L "$codex_dir/external-skill"
assert_true "uninstall preserves cache" test -d "$CACHE_DIR/repository"

printf '\n'
if [ "$FAIL" -gt 0 ]; then
  printf '\033[0;31m%d failed\033[0m, %d passed\n' "$FAIL" "$PASS" >&2
  exit 1
fi
printf '\033[0;32m%d passed\033[0m\n' "$PASS"

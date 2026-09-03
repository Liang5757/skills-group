#!/usr/bin/env bash

# Cross-platform skill installer entrypoint for macOS (Bash 3.2+).
# The installer keeps a validated repository cache and links skills into each
# supported agent's user-level skill directory.

set -u

REPOSITORY="Liang5757/skills-group"
REPOSITORY_REF="main"
API_URL_DEFAULT="https://api.github.com/repos/$REPOSITORY/git/ref/heads/$REPOSITORY_REF"
ARCHIVE_URL_DEFAULT="https://github.com/$REPOSITORY/archive"
SUPPORTED_AGENTS="codex claude trae trae-cn"
SKILLS_RELATIVE_PATH=".agents/skills"

USER_HOME="${SKILLS_GROUP_USER_HOME:-$HOME}"
CACHE_ROOT="${SKILLS_GROUP_HOME:-$USER_HOME/.skills-group}"
REPOSITORY_DIR="$CACHE_ROOT/repository"
VERSION_FILE="$CACHE_ROOT/version"
BACKUP_ROOT="$CACHE_ROOT/backups"
API_URL="${SKILLS_GROUP_API_URL:-$API_URL_DEFAULT}"
ARCHIVE_URL="${SKILLS_GROUP_ARCHIVE_URL:-$ARCHIVE_URL_DEFAULT}"
LOCAL_SOURCE="${SKILLS_GROUP_SOURCE_ROOT:-}"
REMOTE_SHA_OVERRIDE="${SKILLS_GROUP_REMOTE_SHA:-}"
DISABLE_COMMAND_DETECTION="${SKILLS_GROUP_DISABLE_COMMAND_DETECTION:-0}"

MODE="install"
FORCE=0
UPDATE_EXPLICIT=0
REQUESTED_AGENTS=""
REQUESTED_SKILLS=""
STAGE_DIR=""
REMOTE_SHA=""

info() { printf '%s\n' "$*"; }
warn() { printf 'Warning: %s\n' "$*" >&2; }
error() { printf 'Error: %s\n' "$*" >&2; }

usage() {
  cat <<'EOF'
Usage: install.sh [options]

With no options, detect supported agents, check for updates, and install every skill.

Options:
  --agent <name>    Install for codex, claude, trae, or trae-cn (repeatable)
  --skill <name>    Install only one skill (repeatable)
  --check           Check whether a newer repository version is available
  --update          Check for updates and install (the default behavior)
  --status          Show cache, remote, and per-agent installation status
  --uninstall       Remove only links managed by Skills Group
  --force           Redownload the current version and rebuild links
  --help            Show this help
EOF
}

cleanup_stage() {
  if [ -n "$STAGE_DIR" ] && [ -d "$STAGE_DIR" ]; then
    case "$STAGE_DIR" in
      "$CACHE_ROOT"/.stage.*) rm -rf "$STAGE_DIR" ;;
    esac
  fi
}
trap cleanup_stage EXIT HUP INT TERM

append_unique_word() {
  current="$1"
  candidate="$2"
  case " $current " in
    *" $candidate "*) printf '%s' "$current" ;;
    *)
      if [ -n "$current" ]; then
        printf '%s %s' "$current" "$candidate"
      else
        printf '%s' "$candidate"
      fi
      ;;
  esac
}

is_supported_agent() {
  case " $SUPPORTED_AGENTS " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}

set_mode() {
  requested="$1"
  if [ "$MODE" != "install" ] && [ "$MODE" != "$requested" ]; then
    error "--check, --status, and --uninstall cannot be combined"
    exit 2
  fi
  MODE="$requested"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent)
      [ "$#" -ge 2 ] || { error "--agent requires a value"; exit 2; }
      is_supported_agent "$2" || { error "unsupported agent: $2"; exit 2; }
      REQUESTED_AGENTS="$(append_unique_word "$REQUESTED_AGENTS" "$2")"
      shift 2
      ;;
    --skill)
      [ "$#" -ge 2 ] || { error "--skill requires a value"; exit 2; }
      case "$2" in
        ''|*[!a-z0-9-]*) error "invalid skill name: $2"; exit 2 ;;
      esac
      REQUESTED_SKILLS="$(append_unique_word "$REQUESTED_SKILLS" "$2")"
      shift 2
      ;;
    --check) set_mode "check"; shift ;;
    --update) UPDATE_EXPLICIT=1; shift ;;
    --status) set_mode "status"; shift ;;
    --uninstall) set_mode "uninstall"; shift ;;
    --force) FORCE=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) error "unknown option: $1"; usage >&2; exit 2 ;;
  esac
done

if [ "$UPDATE_EXPLICIT" -eq 1 ] && [ "$MODE" != "install" ]; then
  error "--update cannot be combined with --check, --status, or --uninstall"
  exit 2
fi

agent_dir() {
  case "$1" in
    codex) printf '%s/.agents/skills\n' "$USER_HOME" ;;
    claude) printf '%s/.claude/skills\n' "$USER_HOME" ;;
    trae) printf '%s/.trae/skills\n' "$USER_HOME" ;;
    trae-cn) printf '%s/.trae-cn/skills\n' "$USER_HOME" ;;
    *) return 1 ;;
  esac
}

agent_exists() {
  case "$1" in
    codex)
      [ -d "$USER_HOME/.codex" ] || [ -d "$USER_HOME/.agents" ] ||
        { [ "$DISABLE_COMMAND_DETECTION" != "1" ] && command -v codex >/dev/null 2>&1; }
      ;;
    claude)
      [ -d "$USER_HOME/.claude" ] ||
        { [ "$DISABLE_COMMAND_DETECTION" != "1" ] && command -v claude >/dev/null 2>&1; }
      ;;
    trae) [ -d "$USER_HOME/.trae" ] ;;
    trae-cn) [ -d "$USER_HOME/.trae-cn" ] ;;
    *) return 1 ;;
  esac
}

detect_agents() {
  detected=""
  for agent in $SUPPORTED_AGENTS; do
    if agent_exists "$agent"; then
      detected="$(append_unique_word "$detected" "$agent")"
    fi
  done
  printf '%s\n' "$detected"
}

read_local_version() {
  if [ -f "$VERSION_FILE" ]; then
    tr -d '[:space:]' < "$VERSION_FILE"
  fi
}

fetch_remote_sha() {
  if [ -n "$REMOTE_SHA_OVERRIDE" ]; then
    REMOTE_SHA="$REMOTE_SHA_OVERRIDE"
    return 0
  fi

  if [ -n "$LOCAL_SOURCE" ]; then
    REMOTE_SHA="local"
    return 0
  fi

  if ! command -v curl >/dev/null 2>&1; then
    return 1
  fi

  response="$(curl -fsSL --connect-timeout 10 --max-time 30 "$API_URL" 2>/dev/null)" || return 1
  REMOTE_SHA="$(printf '%s\n' "$response" | sed -n 's/.*"sha"[[:space:]]*:[[:space:]]*"\([0-9a-fA-F]\{40\}\)".*/\1/p' | head -n 1)"
  [ -n "$REMOTE_SHA" ]
}

frontmatter_name() {
  awk -F: '
  NR == 1 && $0 == "---" { frontmatter = 1; next }
  frontmatter && $0 == "---" { exit }
  frontmatter && /^name:[[:space:]]*/ {
    sub(/^[[:space:]]*/, "", $2)
    gsub(/["\047]/, "", $2)
    print $2
    exit
  }' "$1"
}

validate_repository() {
  root="$1"
  skills_root="$root/$SKILLS_RELATIVE_PATH"
  [ -d "$skills_root" ] || { error "repository does not contain $SKILLS_RELATIVE_PATH/"; return 1; }

  names=""
  found=0
  invalid=0

  while IFS= read -r skill_md; do
    [ -n "$skill_md" ] || continue
    found=$((found + 1))
    directory_name="$(basename "$(dirname "$skill_md")")"
    declared_name="$(frontmatter_name "$skill_md")"
    case "$directory_name" in
      ''|*[!a-z0-9-]*)
        error "invalid skill directory name: $directory_name"
        invalid=1
        ;;
    esac
    if [ "$declared_name" != "$directory_name" ]; then
      error "skill name mismatch: $skill_md declares '$declared_name'"
      invalid=1
    fi
    names="${names}
${directory_name}"
  done <<EOF
$(find "$skills_root" -type f -name SKILL.md -not -path '*/node_modules/*' | sort)
EOF

  if [ "$found" -eq 0 ]; then
    error "repository contains no skills"
    invalid=1
  fi

  duplicate="$(printf '%s\n' "$names" | sed '/^$/d' | sort | uniq -d | head -n 1)"
  if [ -n "$duplicate" ]; then
    error "duplicate skill name: $duplicate"
    invalid=1
  fi

  [ "$invalid" -eq 0 ]
}

cache_is_valid() {
  [ -d "$REPOSITORY_DIR" ] && validate_repository "$REPOSITORY_DIR" >/dev/null 2>&1
}

extract_archive() {
  archive="$1"
  destination="$2"
  mkdir -p "$destination" || return 1
  if command -v ditto >/dev/null 2>&1; then
    ditto -x -k "$archive" "$destination"
  elif command -v unzip >/dev/null 2>&1; then
    unzip -q "$archive" -d "$destination"
  else
    error "neither ditto nor unzip is available"
    return 1
  fi
}

stage_repository() {
  mkdir -p "$CACHE_ROOT" || return 1
  STAGE_DIR="$CACHE_ROOT/.stage.$$"
  rm -rf "$STAGE_DIR"
  mkdir -p "$STAGE_DIR/repository" || return 1

  if [ -n "$LOCAL_SOURCE" ]; then
    [ -d "$LOCAL_SOURCE/$SKILLS_RELATIVE_PATH" ] || { error "SKILLS_GROUP_SOURCE_ROOT has no $SKILLS_RELATIVE_PATH/: $LOCAL_SOURCE"; return 1; }
    mkdir -p "$STAGE_DIR/repository/$SKILLS_RELATIVE_PATH" || return 1
    cp -R "$LOCAL_SOURCE/$SKILLS_RELATIVE_PATH"/. "$STAGE_DIR/repository/$SKILLS_RELATIVE_PATH" || return 1
  else
    archive="$STAGE_DIR/repository.zip"
    archive_url="$ARCHIVE_URL/$REMOTE_SHA.zip"
    info "Downloading Skills Group $REMOTE_SHA..."
    curl -fsSL --connect-timeout 10 --max-time 120 "$archive_url" -o "$archive" || return 1
    extract_root="$STAGE_DIR/extracted"
    extract_archive "$archive" "$extract_root" || return 1
    extracted_dir="$(find "$extract_root" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
    [ -n "$extracted_dir" ] || { error "downloaded archive is empty"; return 1; }
    rm -rf "$STAGE_DIR/repository"
    mv "$extracted_dir" "$STAGE_DIR/repository" || return 1
  fi

  validate_repository "$STAGE_DIR/repository"
}

promote_repository() {
  previous="$CACHE_ROOT/repository.previous.$$"
  version_tmp="$CACHE_ROOT/version.$$"
  rm -rf "$previous"

  if [ -d "$REPOSITORY_DIR" ]; then
    mv "$REPOSITORY_DIR" "$previous" || return 1
  fi

  if ! mv "$STAGE_DIR/repository" "$REPOSITORY_DIR"; then
    [ -d "$previous" ] && mv "$previous" "$REPOSITORY_DIR"
    return 1
  fi

  if ! printf '%s\n' "$REMOTE_SHA" > "$version_tmp" || ! mv "$version_tmp" "$VERSION_FILE"; then
    rm -rf "$REPOSITORY_DIR"
    [ -d "$previous" ] && mv "$previous" "$REPOSITORY_DIR"
    return 1
  fi

  rm -rf "$previous"
  info "Cache updated to $REMOTE_SHA."
}

ensure_cache() {
  local_version="$(read_local_version)"
  remote_available=1
  if ! fetch_remote_sha; then
    remote_available=0
  fi

  if [ "$remote_available" -eq 0 ]; then
    if cache_is_valid; then
      warn "could not check GitHub; using cached version ${local_version:-unknown}"
      return 0
    fi
    error "could not check GitHub and no valid cache is available"
    return 1
  fi

  if [ "$FORCE" -eq 0 ] && [ "$local_version" = "$REMOTE_SHA" ] && cache_is_valid; then
    info "Cache is up to date ($REMOTE_SHA)."
    return 0
  fi

  if ! stage_repository; then
    if cache_is_valid; then
      warn "update failed; keeping cached version ${local_version:-unknown}"
      return 0
    fi
    error "downloaded repository could not be prepared"
    return 1
  fi

  if ! promote_repository; then
    error "could not activate the new cache; previous version restored"
    return 1
  fi
}

skill_dir_for_name() {
  name="$1"
  find "$REPOSITORY_DIR/$SKILLS_RELATIVE_PATH" -type f -path "*/$name/SKILL.md" -not -path '*/node_modules/*' -print | head -n 1 | sed 's#/SKILL.md$##'
}

all_skill_names() {
  find "$REPOSITORY_DIR/$SKILLS_RELATIVE_PATH" -type f -name SKILL.md -not -path '*/node_modules/*' -exec dirname {} \; | while IFS= read -r directory; do basename "$directory"; done | sort
}

resolved_skill_names() {
  if [ -n "$REQUESTED_SKILLS" ]; then
    for name in $REQUESTED_SKILLS; do
      directory="$(skill_dir_for_name "$name")"
      [ -n "$directory" ] || { error "unknown skill: $name"; return 1; }
      printf '%s\n' "$name"
    done
  else
    all_skill_names
  fi
}

link_target() {
  [ -L "$1" ] || return 1
  readlink "$1"
}

is_managed_link() {
  target="$(link_target "$1" 2>/dev/null)" || return 1
  case "$target" in
    "$REPOSITORY_DIR"/"$SKILLS_RELATIVE_PATH"/*) return 0 ;;
    "$REPOSITORY_DIR"/skills/*) return 0 ;; # Legacy cache layout.
    *) return 1 ;;
  esac
}

backup_destination() {
  agent="$1"
  name="$2"
  destination="$3"
  timestamp="$(date -u '+%Y%m%dT%H%M%SZ').$$"
  backup_dir="$BACKUP_ROOT/$timestamp/$agent"
  mkdir -p "$backup_dir" || return 1
  backup="$backup_dir/$name"
  mv "$destination" "$backup" || return 1
  printf '%s\n' "$backup"
}

cleanup_stale_managed_links() {
  target_dir="$1"
  [ -d "$target_dir" ] || return 0
  for destination in "$target_dir"/*; do
    [ -L "$destination" ] || continue
    is_managed_link "$destination" || continue
    target="$(link_target "$destination")"
    if [ ! -f "$target/SKILL.md" ]; then
      rm "$destination"
      info "Removed stale managed link: $destination"
    fi
  done
}

install_skill_for_agent() {
  agent="$1"
  name="$2"
  target_dir="$(agent_dir "$agent")"
  source_dir="$(skill_dir_for_name "$name")"
  destination="$target_dir/$name"
  backup=""

  mkdir -p "$target_dir" || return 1

  if [ -L "$destination" ] && is_managed_link "$destination"; then
    rm "$destination" || return 1
  elif [ -e "$destination" ] || [ -L "$destination" ]; then
    backup="$(backup_destination "$agent" "$name" "$destination")" || return 1
    warn "backed up existing $destination to $backup"
  fi

  if ! ln -s "$source_dir" "$destination"; then
    [ -n "$backup" ] && mv "$backup" "$destination"
    return 1
  fi
}

install_for_agents() {
  agents="$1"
  skills="$(resolved_skill_names)" || return 1
  installed=0
  for agent in $agents; do
    target_dir="$(agent_dir "$agent")"
    cleanup_stale_managed_links "$target_dir" || return 1
    for name in $skills; do
      install_skill_for_agent "$agent" "$name" || {
        error "failed to install $name for $agent"
        return 1
      }
      installed=$((installed + 1))
    done
    info "[$agent] linked $(printf '%s\n' "$skills" | wc -l | tr -d ' ') skills -> $target_dir"
  done
  info "Done. $installed links are managed by Skills Group. Restart your agent if changes are not visible."
}

uninstall_for_agents() {
  agents="$1"
  removed=0
  for agent in $agents; do
    target_dir="$(agent_dir "$agent")"
    [ -d "$target_dir" ] || continue
    for destination in "$target_dir"/*; do
      [ -L "$destination" ] || continue
      is_managed_link "$destination" || continue
      name="$(basename "$destination")"
      if [ -n "$REQUESTED_SKILLS" ]; then
        case " $REQUESTED_SKILLS " in *" $name "*) ;; *) continue ;; esac
      fi
      rm "$destination" || return 1
      removed=$((removed + 1))
    done
  done
  info "Removed $removed managed links. Cache and backups remain in $CACHE_ROOT."
}

count_managed_links() {
  target_dir="$1"
  count=0
  if [ -d "$target_dir" ]; then
    for destination in "$target_dir"/*; do
      [ -L "$destination" ] || continue
      if is_managed_link "$destination"; then count=$((count + 1)); fi
    done
  fi
  printf '%s\n' "$count"
}

show_status() {
  local_version="$(read_local_version)"
  if fetch_remote_sha; then remote_display="$REMOTE_SHA"; else remote_display="unavailable"; fi
  if cache_is_valid; then cache_display="valid"; else cache_display="missing or invalid"; fi

  info "Skills Group status"
  info "  cache:   $cache_display ($REPOSITORY_DIR)"
  info "  local:   ${local_version:-none}"
  info "  remote:  $remote_display"
  for agent in $SUPPORTED_AGENTS; do
    target_dir="$(agent_dir "$agent")"
    if agent_exists "$agent"; then detected="detected"; else detected="not detected"; fi
    info "  $agent: $detected, $(count_managed_links "$target_dir") managed links -> $target_dir"
  done
}

check_update() {
  local_version="$(read_local_version)"
  if ! fetch_remote_sha; then
    error "could not determine the remote version"
    return 1
  fi
  if [ "$local_version" = "$REMOTE_SHA" ] && cache_is_valid; then
    info "Skills Group is up to date ($REMOTE_SHA)."
    return 0
  fi
  info "Update available: ${local_version:-not installed} -> $REMOTE_SHA"
  return 10
}

case "$MODE" in
  check)
    check_update
    exit $?
    ;;
  status)
    show_status
    exit 0
    ;;
  uninstall)
    if [ -n "$REQUESTED_AGENTS" ]; then agents="$REQUESTED_AGENTS"; else agents="$SUPPORTED_AGENTS"; fi
    uninstall_for_agents "$agents"
    exit $?
    ;;
esac

if [ -n "$REQUESTED_AGENTS" ]; then
  AGENTS="$REQUESTED_AGENTS"
else
  AGENTS="$(detect_agents)"
fi

if [ -z "$AGENTS" ]; then
  error "no supported agents detected; use --agent codex, claude, trae, or trae-cn"
  exit 1
fi

ensure_cache || exit 1
install_for_agents "$AGENTS"

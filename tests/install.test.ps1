$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Installer = Join-Path $RepoRoot "install.ps1"
$Sandbox = Join-Path ([IO.Path]::GetTempPath()) ("skills-group-test-" + [Guid]::NewGuid().ToString("N"))
$UserDir = Join-Path $Sandbox "User Home 测试"
$CacheDir = Join-Path $Sandbox "Cache Root"
$FixtureDir = Join-Path $Sandbox "fixture"
$InvalidDir = Join-Path $Sandbox "invalid"
$Pass = 0
$Fail = 0

function Assert-True([string]$Label, [bool]$Condition) {
    if ($Condition) {
        $script:Pass++
        Write-Host "  + $Label" -ForegroundColor Green
    } else {
        $script:Fail++
        Write-Host "  x $Label" -ForegroundColor Red
    }
}

function Assert-Equal([string]$Label, $Expected, $Actual) {
    Assert-True "$Label (expected '$Expected', got '$Actual')" ($Expected -eq $Actual)
}

function Invoke-Installer {
    param(
        [string]$SourceRoot,
        [string]$RemoteSha,
        [string[]]$Arguments = @()
    )
    $env:SKILLS_GROUP_USER_HOME = $UserDir
    $env:SKILLS_GROUP_HOME = $CacheDir
    $env:SKILLS_GROUP_SOURCE_ROOT = $SourceRoot
    $env:SKILLS_GROUP_REMOTE_SHA = $RemoteSha
    $env:SKILLS_GROUP_DISABLE_COMMAND_DETECTION = "1"
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $Installer @Arguments | Out-Host
    return $LASTEXITCODE
}

try {
    New-Item -ItemType Directory -Path (Join-Path $UserDir ".codex") -Force | Out-Null

    Write-Host "Read-only status"
    $rc = Invoke-Installer $RepoRoot "version-one" @("-Status")
    Assert-Equal "status succeeds" 0 $rc
    Assert-True "status does not create the cache" (-not (Test-Path -LiteralPath $CacheDir))

    Write-Host "Initial install and detection"
    $rc = Invoke-Installer $RepoRoot "version-one"
    Assert-Equal "initial install succeeds" 0 $rc
    $codexDir = Join-Path $UserDir ".agents\skills"
    $links = @(Get-ChildItem -LiteralPath $codexDir -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })
    Assert-Equal "all eight skills are junctioned" 8 $links.Count
    Assert-True "junction resolves through a path containing spaces" (Test-Path -LiteralPath (Join-Path $codexDir "changelog-generator\SKILL.md"))
    Assert-True "undetected Claude is not modified" (-not (Test-Path -LiteralPath (Join-Path $UserDir ".claude\skills")))

    Write-Host "Idempotency and conflict backup"
    $rc = Invoke-Installer $RepoRoot "version-one"
    Assert-Equal "idempotent reinstall succeeds" 0 $rc
    Assert-True "idempotent reinstall creates no backup" (-not (Test-Path -LiteralPath (Join-Path $CacheDir "backups")))
    $conflict = Join-Path $UserDir ".claude\skills\changelog-generator"
    New-Item -ItemType Directory -Path $conflict -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $conflict "user.txt"), "user-owned")
    $rc = Invoke-Installer $RepoRoot "version-one" @("-Agent", "claude", "-Skill", "changelog-generator")
    Assert-Equal "selected agent and skill install succeeds" 0 $rc
    $conflictItem = Get-Item -LiteralPath $conflict -Force
    Assert-True "conflicting directory becomes a junction" ([bool]($conflictItem.Attributes -band [IO.FileAttributes]::ReparsePoint))
    $backupFiles = @(Get-ChildItem -LiteralPath (Join-Path $CacheDir "backups") -Filter "user.txt" -File -Recurse)
    Assert-Equal "conflicting content is backed up" 1 $backupFiles.Count

    Write-Host "Version checks"
    $rc = Invoke-Installer $RepoRoot "version-one" @("-Check")
    Assert-Equal "current version returns zero" 0 $rc
    $rc = Invoke-Installer $RepoRoot "version-two" @("-Check")
    Assert-Equal "available update returns ten" 10 $rc

    Write-Host "Update and stale-link cleanup"
    New-Item -ItemType Directory -Path $FixtureDir -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $RepoRoot "skills") -Destination (Join-Path $FixtureDir "skills") -Recurse
    Remove-Item -LiteralPath (Join-Path $FixtureDir "skills\video-downloader") -Recurse -Force
    $externalSource = Join-Path $Sandbox "external-source"
    New-Item -ItemType Directory -Path $externalSource -Force | Out-Null
    New-Item -ItemType Junction -Path (Join-Path $codexDir "external-skill") -Target $externalSource | Out-Null
    $rc = Invoke-Installer $FixtureDir "version-two"
    Assert-Equal "update succeeds" 0 $rc
    Assert-True "removed upstream skill junction is cleaned" (-not (Test-Path -LiteralPath (Join-Path $codexDir "video-downloader")))
    Assert-True "external junction is preserved" (Test-Path -LiteralPath (Join-Path $codexDir "external-skill"))
    Assert-Equal "new version is recorded" "version-two" ([IO.File]::ReadAllText((Join-Path $CacheDir "version")).Trim())

    Write-Host "Invalid update rollback"
    $badSkillDir = Join-Path $InvalidDir "skills\bad-skill"
    New-Item -ItemType Directory -Path $badSkillDir -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $badSkillDir "SKILL.md"), "---`nname: other-name`ndescription: invalid fixture`n---`n")
    $rc = Invoke-Installer $InvalidDir "version-three" @("-Force")
    Assert-Equal "invalid update falls back to cache" 0 $rc
    Assert-Equal "invalid update keeps previous version" "version-two" ([IO.File]::ReadAllText((Join-Path $CacheDir "version")).Trim())

    Write-Host "Safe uninstall"
    $rc = Invoke-Installer $FixtureDir "version-two" @("-Uninstall")
    Assert-Equal "uninstall succeeds" 0 $rc
    $managedRemaining = @(Get-ChildItem -LiteralPath $codexDir -Force | Where-Object { $_.Name -ne "external-skill" })
    Assert-Equal "uninstall removes managed junctions" 0 $managedRemaining.Count
    Assert-True "uninstall preserves external junction" (Test-Path -LiteralPath (Join-Path $codexDir "external-skill"))
    Assert-True "uninstall preserves cache" (Test-Path -LiteralPath (Join-Path $CacheDir "repository"))
} finally {
    if (Test-Path -LiteralPath $Sandbox) {
        Remove-Item -LiteralPath $Sandbox -Recurse -Force
    }
}

Write-Host ""
if ($Fail -gt 0) {
    Write-Host "$Fail failed, $Pass passed" -ForegroundColor Red
    exit 1
}
Write-Host "$Pass passed" -ForegroundColor Green

#requires -Version 5.1

<#
.SYNOPSIS
Installs and updates Skills Group skills for supported Windows agents.

.DESCRIPTION
With no options, the script detects Codex, Claude Code, Trae, and Trae CN,
updates a validated local cache, and creates directory junctions for every skill.
#>

[CmdletBinding()]
param(
    [ValidateSet("codex", "claude", "trae", "trae-cn")]
    [string[]]$Agent,
    [ValidatePattern("^[a-z0-9][a-z0-9-]*$")]
    [string[]]$Skill,
    [switch]$Check,
    [switch]$Update,
    [switch]$Status,
    [switch]$Uninstall,
    [switch]$Force,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$Repository = "Liang5757/skills-group"
$RepositoryRef = "main"
$SupportedAgents = @("codex", "claude", "trae", "trae-cn")
$UserHome = if ($env:SKILLS_GROUP_USER_HOME) {
    $env:SKILLS_GROUP_USER_HOME
} else {
    [Environment]::GetFolderPath("UserProfile")
}
$CacheRoot = if ($env:SKILLS_GROUP_HOME) {
    $env:SKILLS_GROUP_HOME
} else {
    Join-Path $UserHome ".skills-group"
}
$RepositoryDir = Join-Path $CacheRoot "repository"
$VersionFile = Join-Path $CacheRoot "version"
$BackupRoot = Join-Path $CacheRoot "backups"
$ApiUrl = if ($env:SKILLS_GROUP_API_URL) {
    $env:SKILLS_GROUP_API_URL
} else {
    "https://api.github.com/repos/$Repository/git/ref/heads/$RepositoryRef"
}
$ArchiveUrl = if ($env:SKILLS_GROUP_ARCHIVE_URL) {
    $env:SKILLS_GROUP_ARCHIVE_URL
} else {
    "https://github.com/$Repository/archive"
}
$LocalSource = $env:SKILLS_GROUP_SOURCE_ROOT
$RemoteShaOverride = $env:SKILLS_GROUP_REMOTE_SHA
$DisableCommandDetection = $env:SKILLS_GROUP_DISABLE_COMMAND_DETECTION -eq "1"
$script:StageDir = $null
$script:RemoteSha = $null

function Write-Info([string]$Message) {
    Write-Host $Message
}

function Write-WarningMessage([string]$Message) {
    Write-Warning $Message
}

function Write-ErrorMessage([string]$Message) {
    [Console]::Error.WriteLine("Error: $Message")
}

function Show-Help {
    @"
Usage: install.ps1 [options]

With no options, detect supported agents, check for updates, and install every skill.

Options:
  -Agent <name[]>   Install for codex, claude, trae, or trae-cn
  -Skill <name[]>   Install only selected skills
  -Check            Check whether a newer repository version is available
  -Update           Check for updates and install (the default behavior)
  -Status           Show cache, remote, and per-agent installation status
  -Uninstall        Remove only junctions managed by Skills Group
  -Force            Redownload the current version and rebuild junctions
  -Help             Show this help
"@ | Write-Host
}

function Get-AgentDirectory([string]$Name) {
    switch ($Name) {
        "codex" { return (Join-Path $UserHome ".agents\skills") }
        "claude" { return (Join-Path $UserHome ".claude\skills") }
        "trae" { return (Join-Path $UserHome ".trae\skills") }
        "trae-cn" { return (Join-Path $UserHome ".trae-cn\skills") }
        default { throw "Unsupported agent: $Name" }
    }
}

function Test-AgentExists([string]$Name) {
    switch ($Name) {
        "codex" {
            return (Test-Path -LiteralPath (Join-Path $UserHome ".codex") -PathType Container) -or
                (Test-Path -LiteralPath (Join-Path $UserHome ".agents") -PathType Container) -or
                ((-not $DisableCommandDetection) -and $null -ne (Get-Command codex -ErrorAction SilentlyContinue))
        }
        "claude" {
            return (Test-Path -LiteralPath (Join-Path $UserHome ".claude") -PathType Container) -or
                ((-not $DisableCommandDetection) -and $null -ne (Get-Command claude -ErrorAction SilentlyContinue))
        }
        "trae" { return (Test-Path -LiteralPath (Join-Path $UserHome ".trae") -PathType Container) }
        "trae-cn" { return (Test-Path -LiteralPath (Join-Path $UserHome ".trae-cn") -PathType Container) }
        default { return $false }
    }
}

function Get-DetectedAgents {
    return @($SupportedAgents | Where-Object { Test-AgentExists $_ })
}

function Get-LocalVersion {
    if (Test-Path -LiteralPath $VersionFile -PathType Leaf) {
        return ([IO.File]::ReadAllText($VersionFile)).Trim()
    }
    return $null
}

function Get-RemoteSha {
    if ($RemoteShaOverride) {
        $script:RemoteSha = $RemoteShaOverride
        return $true
    }
    if ($LocalSource) {
        $script:RemoteSha = "local"
        return $true
    }
    try {
        $headers = @{ "User-Agent" = "skills-group-installer" }
        $response = Invoke-RestMethod -Uri $ApiUrl -Headers $headers -UseBasicParsing -TimeoutSec 30
        $sha = [string]$response.object.sha
        if ($sha -notmatch "^[0-9a-fA-F]{40}$") {
            return $false
        }
        $script:RemoteSha = $sha
        return $true
    } catch {
        return $false
    }
}

function Get-SkillMetadata([string]$Root) {
    $skillsRoot = Join-Path $Root "skills"
    if (-not (Test-Path -LiteralPath $skillsRoot -PathType Container)) {
        throw "Repository does not contain skills/."
    }

    $metadata = @()
    $skillFiles = @(Get-ChildItem -LiteralPath $skillsRoot -Filter "SKILL.md" -File -Recurse |
        Where-Object { $_.FullName -notmatch "[\\/]node_modules[\\/]" } |
        Sort-Object FullName)
    if ($skillFiles.Count -eq 0) {
        throw "Repository contains no skills."
    }

    foreach ($file in $skillFiles) {
        $directoryName = $file.Directory.Name
        if ($directoryName -notmatch "^[a-z0-9][a-z0-9-]*$") {
            throw "Invalid skill directory name: $directoryName"
        }
        $declaredName = $null
        $inFrontmatter = $false
        $lineNumber = 0
        foreach ($line in [IO.File]::ReadLines($file.FullName)) {
            $lineNumber++
            if ($lineNumber -eq 1 -and $line -eq "---") {
                $inFrontmatter = $true
                continue
            }
            if ($inFrontmatter -and $line -eq "---") {
                break
            }
            if ($inFrontmatter -and $line -match '^name:\s*["'']?([^"'']+)["'']?\s*$') {
                $declaredName = $Matches[1]
                break
            }
        }
        if ($declaredName -ne $directoryName) {
            throw "Skill name mismatch: $($file.FullName) declares '$declaredName'."
        }
        $metadata += [pscustomobject]@{
            Name = $directoryName
            Directory = $file.Directory.FullName
        }
    }

    $duplicate = $metadata | Group-Object Name | Where-Object Count -gt 1 | Select-Object -First 1
    if ($null -ne $duplicate) {
        throw "Duplicate skill name: $($duplicate.Name)"
    }
    return @($metadata)
}

function Test-CacheValid {
    try {
        $null = Get-SkillMetadata $RepositoryDir
        return $true
    } catch {
        return $false
    }
}

function Copy-DirectoryContents([string]$Source, [string]$Destination) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

function Stage-Repository {
    New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null
    $script:StageDir = Join-Path $CacheRoot ".stage.$PID"
    if (Test-Path -LiteralPath $script:StageDir) {
        Remove-Item -LiteralPath $script:StageDir -Recurse -Force
    }
    $stagedRepository = Join-Path $script:StageDir "repository"
    New-Item -ItemType Directory -Path $stagedRepository -Force | Out-Null

    if ($LocalSource) {
        if (-not (Test-Path -LiteralPath (Join-Path $LocalSource "skills") -PathType Container)) {
            throw "SKILLS_GROUP_SOURCE_ROOT has no skills/: $LocalSource"
        }
        Copy-DirectoryContents (Join-Path $LocalSource "skills") (Join-Path $stagedRepository "skills")
    } else {
        $archive = Join-Path $script:StageDir "repository.zip"
        $downloadUrl = "$ArchiveUrl/$($script:RemoteSha).zip"
        Write-Info "Downloading Skills Group $($script:RemoteSha)..."
        Invoke-WebRequest -Uri $downloadUrl -UseBasicParsing -TimeoutSec 120 -OutFile $archive
        $extractRoot = Join-Path $script:StageDir "extracted"
        Expand-Archive -LiteralPath $archive -DestinationPath $extractRoot -Force
        $extracted = @(Get-ChildItem -LiteralPath $extractRoot -Directory | Select-Object -First 1)
        if ($extracted.Count -eq 0) {
            throw "Downloaded archive is empty."
        }
        Remove-Item -LiteralPath $stagedRepository -Recurse -Force
        Move-Item -LiteralPath $extracted[0].FullName -Destination $stagedRepository
    }

    $null = Get-SkillMetadata $stagedRepository
}

function Promote-Repository {
    $previous = Join-Path $CacheRoot "repository.previous.$PID"
    $versionTemp = Join-Path $CacheRoot "version.$PID"
    if (Test-Path -LiteralPath $previous) {
        Remove-Item -LiteralPath $previous -Recurse -Force
    }

    $hadPrevious = Test-Path -LiteralPath $RepositoryDir -PathType Container
    if ($hadPrevious) {
        Move-Item -LiteralPath $RepositoryDir -Destination $previous
    }

    try {
        Move-Item -LiteralPath (Join-Path $script:StageDir "repository") -Destination $RepositoryDir
        [IO.File]::WriteAllText($versionTemp, "$($script:RemoteSha)`n", [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $versionTemp -Destination $VersionFile -Force
    } catch {
        if (Test-Path -LiteralPath $RepositoryDir) {
            Remove-Item -LiteralPath $RepositoryDir -Recurse -Force
        }
        if ($hadPrevious -and (Test-Path -LiteralPath $previous)) {
            Move-Item -LiteralPath $previous -Destination $RepositoryDir
        }
        throw
    }

    if (Test-Path -LiteralPath $previous) {
        Remove-Item -LiteralPath $previous -Recurse -Force
    }
    Write-Info "Cache updated to $($script:RemoteSha)."
}

function Ensure-Cache {
    $localVersion = Get-LocalVersion
    if (-not (Get-RemoteSha)) {
        if (Test-CacheValid) {
            Write-WarningMessage "Could not check GitHub; using cached version $(if ($localVersion) { $localVersion } else { 'unknown' })."
            return
        }
        throw "Could not check GitHub and no valid cache is available."
    }

    if ((-not $Force) -and $localVersion -eq $script:RemoteSha -and (Test-CacheValid)) {
        Write-Info "Cache is up to date ($($script:RemoteSha))."
        return
    }

    try {
        Stage-Repository
        Promote-Repository
    } catch {
        if (Test-CacheValid) {
            Write-WarningMessage "Update failed; keeping cached version $(if ($localVersion) { $localVersion } else { 'unknown' }): $($_.Exception.Message)"
            return
        }
        throw
    }
}

function Get-ResolvedSkills {
    $metadata = @(Get-SkillMetadata $RepositoryDir)
    if (-not $Skill -or $Skill.Count -eq 0) {
        return @($metadata | Sort-Object Name)
    }

    $selected = @()
    foreach ($name in ($Skill | Select-Object -Unique)) {
        $match = @($metadata | Where-Object Name -eq $name)
        if ($match.Count -eq 0) {
            throw "Unknown skill: $name"
        }
        $selected += $match[0]
    }
    return @($selected)
}

function Get-LinkTarget([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($null -eq $item -or -not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        return $null
    }
    $target = @($item.Target | Select-Object -First 1)
    if ($target.Count -eq 0 -or -not $target[0]) {
        return $null
    }
    return [IO.Path]::GetFullPath([string]$target[0])
}

function Test-ManagedLink([string]$Path) {
    $target = Get-LinkTarget $Path
    if (-not $target) {
        return $false
    }
    $managedRoot = [IO.Path]::GetFullPath((Join-Path $RepositoryDir "skills")) + [IO.Path]::DirectorySeparatorChar
    return $target.StartsWith($managedRoot, [StringComparison]::OrdinalIgnoreCase)
}

function Backup-Destination([string]$AgentName, [string]$SkillName, [string]$Destination) {
    $timestamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ") + ".$PID"
    $backupDir = Join-Path (Join-Path $BackupRoot $timestamp) $AgentName
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    $backup = Join-Path $backupDir $SkillName
    Move-Item -LiteralPath $Destination -Destination $backup
    return $backup
}

function Remove-StaleManagedLinks([string]$TargetDir) {
    if (-not (Test-Path -LiteralPath $TargetDir -PathType Container)) {
        return
    }
    foreach ($item in Get-ChildItem -LiteralPath $TargetDir -Force) {
        if (-not (Test-ManagedLink $item.FullName)) {
            continue
        }
        $target = Get-LinkTarget $item.FullName
        if (-not (Test-Path -LiteralPath (Join-Path $target "SKILL.md") -PathType Leaf)) {
            Remove-Item -LiteralPath $item.FullName -Force
            Write-Info "Removed stale managed junction: $($item.FullName)"
        }
    }
}

function Install-Skill([string]$AgentName, $SkillMetadata) {
    $targetDir = Get-AgentDirectory $AgentName
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    $destination = Join-Path $targetDir $SkillMetadata.Name
    $existing = Get-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
    $backup = $null

    if ($null -ne $existing -and (Test-ManagedLink $destination)) {
        Remove-Item -LiteralPath $destination -Force
    } elseif ($null -ne $existing) {
        $backup = Backup-Destination $AgentName $SkillMetadata.Name $destination
        Write-WarningMessage "Backed up existing $destination to $backup."
    }

    try {
        New-Item -ItemType Junction -Path $destination -Target $SkillMetadata.Directory | Out-Null
    } catch {
        if ($backup -and -not (Test-Path -LiteralPath $destination)) {
            Move-Item -LiteralPath $backup -Destination $destination
        }
        throw
    }
}

function Install-ForAgents([string[]]$AgentNames) {
    $skills = @(Get-ResolvedSkills)
    $installed = 0
    foreach ($agentName in $AgentNames) {
        $targetDir = Get-AgentDirectory $agentName
        Remove-StaleManagedLinks $targetDir
        foreach ($skillMetadata in $skills) {
            Install-Skill $agentName $skillMetadata
            $installed++
        }
        Write-Info "[$agentName] linked $($skills.Count) skills -> $targetDir"
    }
    Write-Info "Done. $installed junctions are managed by Skills Group. Restart your agent if changes are not visible."
}

function Uninstall-ForAgents([string[]]$AgentNames) {
    $removed = 0
    $selectedSkills = if ($Skill) { @($Skill | Select-Object -Unique) } else { @() }
    foreach ($agentName in $AgentNames) {
        $targetDir = Get-AgentDirectory $agentName
        if (-not (Test-Path -LiteralPath $targetDir -PathType Container)) {
            continue
        }
        foreach ($item in Get-ChildItem -LiteralPath $targetDir -Force) {
            if (-not (Test-ManagedLink $item.FullName)) {
                continue
            }
            if ($selectedSkills.Count -gt 0 -and $selectedSkills -notcontains $item.Name) {
                continue
            }
            Remove-Item -LiteralPath $item.FullName -Force
            $removed++
        }
    }
    Write-Info "Removed $removed managed junctions. Cache and backups remain in $CacheRoot."
}

function Get-ManagedLinkCount([string]$TargetDir) {
    if (-not (Test-Path -LiteralPath $TargetDir -PathType Container)) {
        return 0
    }
    return @(Get-ChildItem -LiteralPath $TargetDir -Force | Where-Object { Test-ManagedLink $_.FullName }).Count
}

function Show-Status {
    $localVersion = Get-LocalVersion
    $remoteDisplay = if (Get-RemoteSha) { $script:RemoteSha } else { "unavailable" }
    $cacheDisplay = if (Test-CacheValid) { "valid" } else { "missing or invalid" }
    Write-Info "Skills Group status"
    Write-Info "  cache:   $cacheDisplay ($RepositoryDir)"
    Write-Info "  local:   $(if ($localVersion) { $localVersion } else { 'none' })"
    Write-Info "  remote:  $remoteDisplay"
    foreach ($agentName in $SupportedAgents) {
        $targetDir = Get-AgentDirectory $agentName
        $detected = if (Test-AgentExists $agentName) { "detected" } else { "not detected" }
        Write-Info "  ${agentName}: $detected, $(Get-ManagedLinkCount $targetDir) managed junctions -> $targetDir"
    }
}

function Test-UpdateAvailable {
    $localVersion = Get-LocalVersion
    if (-not (Get-RemoteSha)) {
        Write-ErrorMessage "Could not determine the remote version."
        return 1
    }
    if ($localVersion -eq $script:RemoteSha -and (Test-CacheValid)) {
        Write-Info "Skills Group is up to date ($($script:RemoteSha))."
        return 0
    }
    Write-Info "Update available: $(if ($localVersion) { $localVersion } else { 'not installed' }) -> $($script:RemoteSha)"
    return 10
}

function Invoke-Main {
    if ($Help) {
        Show-Help
        return 0
    }

    $exclusiveModes = @(@($Check, $Status, $Uninstall) | Where-Object { $_ })
    if ($exclusiveModes.Count -gt 1) {
        Write-ErrorMessage "-Check, -Status, and -Uninstall cannot be combined."
        return 2
    }
    if ($Update -and $exclusiveModes.Count -gt 0) {
        Write-ErrorMessage "-Update cannot be combined with -Check, -Status, or -Uninstall."
        return 2
    }

    if ($Check) {
        $checkResult = Test-UpdateAvailable
        return $checkResult
    }
    if ($Status) {
        Show-Status
        return 0
    }
    if ($Uninstall) {
        $agentNames = if ($Agent) { @($Agent | Select-Object -Unique) } else { $SupportedAgents }
        Uninstall-ForAgents $agentNames
        return 0
    }

    $agentNames = if ($Agent) { @($Agent | Select-Object -Unique) } else { @(Get-DetectedAgents) }
    if ($agentNames.Count -eq 0) {
        Write-ErrorMessage "No supported agents detected; use -Agent codex, claude, trae, or trae-cn."
        return 1
    }

    Ensure-Cache
    Install-ForAgents $agentNames
    return 0
}

$exitCode = 1
try {
    $exitCode = Invoke-Main
} catch {
    Write-ErrorMessage $_.Exception.Message
    $exitCode = 1
} finally {
    if ($script:StageDir -and (Test-Path -LiteralPath $script:StageDir)) {
        try {
            Remove-Item -LiteralPath $script:StageDir -Recurse -Force
        } catch {
            Write-WarningMessage "Could not remove temporary directory $($script:StageDir)."
        }
    }
}
if ($MyInvocation.MyCommand.Path) {
    exit $exitCode
}

# When invoked through `irm ... | iex`, do not terminate the caller's PowerShell
# session. Preserve the result for callers that inspect $LASTEXITCODE.
$global:LASTEXITCODE = $exitCode

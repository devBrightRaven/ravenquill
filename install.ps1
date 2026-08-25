param(
    [string]$SkillRoot = (Join-Path $HOME ".agents\skills")
)

$ErrorActionPreference = "Stop"
$RepoDir = $PSScriptRoot
$Dest = Join-Path $SkillRoot "ravenquill"

if (Test-Path -LiteralPath $Dest) {
    Write-Error "Refusing to overwrite existing destination: $Dest"
}

New-Item -ItemType Directory -Path (
    $Dest,
    (Join-Path $Dest "methodology"),
    (Join-Path $Dest "scripts")
) | Out-Null

Copy-Item -LiteralPath (Join-Path $RepoDir "SKILL.md") -Destination (Join-Path $Dest "SKILL.md")
Get-ChildItem -LiteralPath (Join-Path $RepoDir "methodology") -File -Filter "*.md" |
    Copy-Item -Destination (Join-Path $Dest "methodology")
Get-ChildItem -LiteralPath (Join-Path $RepoDir "scripts") -File -Filter "*.py" |
    Copy-Item -Destination (Join-Path $Dest "scripts")

Write-Host "Installed Ravenquill: $Dest"

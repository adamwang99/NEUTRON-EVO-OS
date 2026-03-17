# ======================
# AI Context Master - Auto Install Script
# ======================
# Run this script to auto-apply AI Context Master settings to VS Code
# Run as: .\install-settings.ps1
# ======================

$ErrorActionPreference = "Stop"

# Detect VS Code settings path
$vscodePath = "$env:APPDATA\Code\User\settings.json"
if (-not (Test-Path $vscodePath)) {
    # Create if not exists
    $settingsDir = Split-Path $vscodePath -Parent
    if (-not (Test-Path $settingsDir)) {
        New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
    }
}

# Memory Stack path
$memoryPath = "D:\AI working\ai-context-master"

# Check if memory stack exists
if (-not (Test-Path $memoryPath)) {
    Write-Host "❌ Memory Stack not found at: $memoryPath" -ForegroundColor Red
    Write-Host "Please update MEMORY_STACK_PATH in this script" -ForegroundColor Yellow
    exit 1
}

# Read existing settings or create new
$settings = @{}
if (Test-Path $vscodePath) {
    $content = Get-Content $vscodePath -Raw -Encoding UTF8
    if ($content) {
        try {
            $settings = $content | ConvertFrom-Json -AsHashtable
        } catch {
            $settings = @{}
        }
    }
}

# Add Claude Code settings
$settings["claude-code.contextFiles"] = @(
    "$memoryPath\SOUL.md",
    "$memoryPath\USER.md",
    "$memoryPath\GOVERNANCE.md",
    "$memoryPath\RULES.md",
    "$memoryPath\COORDINATION.md",
    "$memoryPath\WORKFLOW.md",
    "$memoryPath\CH.md",
    "$memoryPath\MEMORY.md",
    "$memoryPath\START.md",
    "$memoryPath\ULTIMATE_PROMPT.md",
    "$memoryPath\AI_CONTEXT_MASTER.md",
    "$memoryPath\MemoryOS\README.md",
    "$memoryPath\MemoryOS\templates\*.md"
)
$settings["claude-code.autoContextLoad"] = $true
$settings["claude-code.parallelTasks"] = $true

# Auto-approve settings (skip permission prompts)
$settings["claude-code.allowWarnings"] = $true
$settings["claude-code.autoApprove"] = $true
$settings["claudeCode.autoApproveEdit"] = $true
$settings["claudeCode.autoApproveDelete"] = $true
$settings["claudeCode.autoApproveCreate"] = $true

# Write settings
$json = $settings | ConvertTo-Json -Depth 10
$json | Set-Content -Path $vscodePath -Encoding UTF8

Write-Host "✅ AI Context Master settings applied!" -ForegroundColor Green
Write-Host "📁 Settings location: $vscodePath" -ForegroundColor Cyan
Write-Host ""
Write-Host "AI Context Master files added:" -ForegroundColor Yellow
Write-Host "  - SOUL.md (AI Context Master Identity)"
Write-Host "  - USER.md (User Preferences)"
Write-Host "  - GOVERNANCE.md (Policy)"
Write-Host "  - RULES.md (Procedures)"
Write-Host "  - COORDINATION.md (Workflow)"
Write-Host "  - WORKFLOW.md (Task Distribution)"
Write-Host "  - CH.md (Context Hub)"
Write-Host "  - MEMORY.md (Knowledge)"
Write-Host "  - START.md (Quick Reference)"
Write-Host "  - ULTIMATE_PROMPT.md (Agent Factory)"
Write-Host "  - AI_CONTEXT_MASTER.md (System Prompt) ⭐ NEW"
Write-Host "  - MemoryOS/README.md (Full Memory OS)"
Write-Host "  - MemoryOS/templates/*.md (Memory templates)"
Write-Host "  - .claude/agents/ (6 Subagents)"
Write-Host ""
Write-Host "Restart VS Code to apply changes!" -ForegroundColor Green

# CCPM Initialization Script for Windows PowerShell

Write-Host ""
Write-Host ""
Write-Host " ██████╗ ██████╗██████╗ ███╗   ███╗"
Write-Host "██╔════╝██╔════╝██╔══██╗████╗ ████║"
Write-Host "██║     ██║     ██████╔╝██╔████╔██║"
Write-Host "╚██████╗╚██████╗██║     ██║ ╚═╝ ██║"
Write-Host " ╚═════╝ ╚═════╝╚═╝     ╚═╝     ╚═╝"
Write-Host ""
Write-Host "┌─────────────────────────────────┐"
Write-Host "│ Claude Code Project Management  │"
Write-Host "│ by https://x.com/aroussi        │"
Write-Host "└─────────────────────────────────┘"
Write-Host "https://github.com/automazeio/ccpm"
Write-Host ""
Write-Host ""

Write-Host "🚀 Initializing Claude Code PM System" -ForegroundColor Green
Write-Host "======================================"
Write-Host ""

# Check for required tools
Write-Host "🔍 Checking dependencies..." -ForegroundColor Cyan

# Check gh CLI
if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "  ✅ GitHub CLI (gh) installed" -ForegroundColor Green
    $ghAvailable = $true
} else {
    Write-Host "  ❌ GitHub CLI (gh) not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "  To install GitHub CLI:" -ForegroundColor Yellow
    Write-Host "  1. Using winget: winget install --id GitHub.cli" -ForegroundColor Yellow
    Write-Host "  2. Using Chocolatey: choco install gh" -ForegroundColor Yellow
    Write-Host "  3. Or download from: https://cli.github.com/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  ⚠️ Continuing without gh CLI (some features will be limited)" -ForegroundColor Yellow
    $ghAvailable = $false
}

# Check gh auth status
if ($ghAvailable) {
    Write-Host ""
    Write-Host "🔐 Checking GitHub authentication..." -ForegroundColor Cyan
    $authStatus = gh auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ GitHub authenticated" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ GitHub not authenticated" -ForegroundColor Yellow
        Write-Host "  Run manually: gh auth login" -ForegroundColor Yellow
    }

    # Check for gh-sub-issue extension
    Write-Host ""
    Write-Host "📦 Checking gh extensions..." -ForegroundColor Cyan
    $extensions = gh extension list 2>&1 | Out-String
    if ($extensions -match "yahsan2/gh-sub-issue") {
        Write-Host "  ✅ gh-sub-issue extension installed" -ForegroundColor Green
    } else {
        Write-Host "  📥 Installing gh-sub-issue extension..." -ForegroundColor Yellow
        try {
            gh extension install yahsan2/gh-sub-issue
            Write-Host "  ✅ Extension installed" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️ Could not install extension automatically" -ForegroundColor Yellow
            Write-Host "  Run manually: gh extension install yahsan2/gh-sub-issue" -ForegroundColor Yellow
        }
    }
}

# Create directory structure
Write-Host ""
Write-Host "📁 Creating directory structure..." -ForegroundColor Cyan
$directories = @(
    ".claude/prds",
    ".claude/epics",
    ".claude/rules",
    ".claude/agents",
    ".claude/scripts/pm"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "  ✅ Directories created" -ForegroundColor Green

# Copy scripts if in main repo
if ((Test-Path "scripts/pm") -and !($PWD.Path -like "*\.claude*")) {
    Write-Host ""
    Write-Host "📝 Copying PM scripts..." -ForegroundColor Cyan
    Copy-Item -Path "scripts/pm/*" -Destination ".claude/scripts/pm/" -Recurse -Force
    Write-Host "  ✅ Scripts copied" -ForegroundColor Green
}

# Check for git
Write-Host ""
Write-Host "🔗 Checking Git configuration..." -ForegroundColor Cyan
if (Get-Command git -ErrorAction SilentlyContinue) {
    try {
        $gitDir = git rev-parse --git-dir 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Git repository detected" -ForegroundColor Green

            # Check remote
            $remotes = git remote -v 2>&1
            if ($remotes -match "origin") {
                $remoteUrl = git remote get-url origin 2>&1
                Write-Host "  ✅ Remote configured: $remoteUrl" -ForegroundColor Green
                
                # Check if remote is the CCPM template repository
                if ($remoteUrl -match "automazeio/ccpm") {
                    Write-Host ""
                    Write-Host "  ⚠️ WARNING: Your remote origin points to the CCPM template repository!" -ForegroundColor Yellow
                    Write-Host "  This means any issues you create will go to the template repo, not your project." -ForegroundColor Yellow
                    Write-Host ""
                    Write-Host "  To fix this:" -ForegroundColor Yellow
                    Write-Host "  1. Fork the repository or create your own on GitHub" -ForegroundColor Yellow
                    Write-Host "  2. Update your remote:" -ForegroundColor Yellow
                    Write-Host "     git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO.git" -ForegroundColor Yellow
                    Write-Host ""
                } elseif ($ghAvailable) {
                    # Create GitHub labels if this is a GitHub repository
                    $repoView = gh repo view 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host ""
                        Write-Host "🏷️ Creating GitHub labels..." -ForegroundColor Cyan
                        
                        $epicCreated = $false
                        $taskCreated = $false
                        
                        # Try to create epic label
                        gh label create "epic" --color "0E8A16" --description "Epic issue containing multiple related tasks" --force 2>&1 | Out-Null
                        if ($LASTEXITCODE -eq 0 -or ((gh label list 2>&1) -match "^epic")) {
                            $epicCreated = $true
                        }
                        
                        # Try to create task label
                        gh label create "task" --color "1D76DB" --description "Individual task within an epic" --force 2>&1 | Out-Null
                        if ($LASTEXITCODE -eq 0 -or ((gh label list 2>&1) -match "^task")) {
                            $taskCreated = $true
                        }
                        
                        # Report results
                        if ($epicCreated -and $taskCreated) {
                            Write-Host "  ✅ GitHub labels created (epic, task)" -ForegroundColor Green
                        } elseif ($epicCreated -or $taskCreated) {
                            Write-Host "  ⚠️ Some GitHub labels created (epic: $epicCreated, task: $taskCreated)" -ForegroundColor Yellow
                        } else {
                            Write-Host "  ❌ Could not create GitHub labels (check repository permissions)" -ForegroundColor Red
                        }
                    } else {
                        Write-Host "  ℹ️ Not a GitHub repository - skipping label creation" -ForegroundColor Gray
                    }
                }
            } else {
                Write-Host "  ⚠️ No remote configured" -ForegroundColor Yellow
                Write-Host "  Add with: git remote add origin <url>" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ⚠️ Not a git repository" -ForegroundColor Yellow
            Write-Host "  Initialize with: git init" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠️ Error checking git configuration: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ❌ Git not found" -ForegroundColor Red
    Write-Host "  Install Git for Windows from: https://git-scm.com/download/win" -ForegroundColor Yellow
}

# Create CLAUDE.md if it doesn't exist
if (!(Test-Path "CLAUDE.md")) {
    Write-Host ""
    Write-Host "📄 Creating CLAUDE.md..." -ForegroundColor Cyan
    $claudeMd = @"
# CLAUDE.md

> Think carefully and implement the most concise solution that changes as little code as possible.

## Project-Specific Instructions

Add your project-specific instructions here.

## Testing

Always run tests before committing:
- ``npm test`` or equivalent for your stack

## Code Style

Follow existing patterns in the codebase.
"@
    Set-Content -Path "CLAUDE.md" -Value $claudeMd
    Write-Host "  ✅ CLAUDE.md created" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "✅ Initialization Complete!" -ForegroundColor Green
Write-Host "=========================="
Write-Host ""
Write-Host "📊 System Status:" -ForegroundColor Cyan
if ($ghAvailable) {
    $ghVersion = gh --version 2>&1 | Select-Object -First 1
    Write-Host "  $ghVersion"
    $extensionCount = (gh extension list 2>&1 | Measure-Object -Line).Lines
    Write-Host "  Extensions: $extensionCount installed"
    $authStatus = gh auth status 2>&1 | Out-String
    if ($authStatus -match 'Logged in to ([^\s]+)') {
        Write-Host "  Auth: Logged in to $($Matches[1])"
    } else {
        Write-Host "  Auth: Not authenticated"
    }
} else {
    Write-Host "  GitHub CLI: Not installed"
}
Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Create your first PRD: /pm:prd-new <feature-name>"
Write-Host "  2. View help: /pm:help"
Write-Host "  3. Check status: /pm:status"
Write-Host ""
Write-Host "📚 Documentation: README.md"

exit 0

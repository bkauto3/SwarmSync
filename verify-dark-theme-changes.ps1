# Dark Theme Verification Script
# Checks for common issues and violations in the dark theme implementation

Write-Host "Starting Dark Theme Verification..." -ForegroundColor Cyan
Write-Host ""

$issues = @()
$warnings = @()
$verified = @()

# Define paths (resolve relative to script location)
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptRoot) {
    $scriptRoot = $PWD
}
$srcPath = Join-Path $scriptRoot "apps\web\src"
$publicPath = Join-Path $scriptRoot "apps\web\public"
# Pre-compute project files (exclude node_modules)
$logoPath = Join-Path $publicPath "swarm-sync-logo.png"
$projectFiles = Get-ChildItem -Path $srcPath -Recurse -Include *.tsx,*.ts,*.css -File |
    Where-Object { $_.FullName -notmatch '\\node_modules\\' } |
    Select-Object -ExpandProperty FullName

# Check 1: Logo file exists
Write-Host "Checking logo file..." -ForegroundColor Yellow
if (Test-Path $logoPath) {
    Write-Host "  Logo file exists" -ForegroundColor Green
    $verified += "Logo file exists"
} else {
    Write-Host "  Logo file NOT found at $logoPath" -ForegroundColor Red
    $issues += "Logo file missing: $logoPath"
}

# Check 2: No yellow colors
Write-Host "Checking for yellow colors..." -ForegroundColor Yellow
$yellowPatterns = @(
    "text-yellow-400",
    "text-yellow-500",
    "text-yellow-600",
    "bg-yellow-400",
    "bg-yellow-500",
    "bg-yellow-600",
    "yellow-400",
    "yellow-500"
)

$yellowFound = $false
foreach ($pattern in $yellowPatterns) {
    $results = Select-String -Path $projectFiles -Pattern $pattern -ErrorAction SilentlyContinue
    if ($results) {
        $yellowFound = $true
        foreach ($result in $results) {
            Write-Host "  Found '$pattern' in $($result.Path):$($result.LineNumber)" -ForegroundColor Yellow
            $warnings += "$($result.Path):$($result.LineNumber) - Found '$pattern'"
        }
    }
}

if (-not $yellowFound) {
    Write-Host "  No yellow colors found" -ForegroundColor Green
    $verified += "No yellow colors"
} else {
    Write-Host "  Yellow colors found (may be intentional)" -ForegroundColor Yellow
}

# Check 3: No brass colors
Write-Host "Checking for brass colors..." -ForegroundColor Yellow
$brassPatterns = @(
    "text-brass",
    "bg-brass",
    "border-brass",
    "brass/",
    "bg-brass/",
    "text-brass/"
)

$brassFound = $false
foreach ($pattern in $brassPatterns) {
    $escapedPattern = [regex]::Escape($pattern)
    $results = Select-String -Path $projectFiles -Pattern $escapedPattern -ErrorAction SilentlyContinue
    if ($results) {
        $brassFound = $true
        foreach ($result in $results) {
            Write-Host "  Found '$pattern' in $($result.Path):$($result.LineNumber)" -ForegroundColor Yellow
            $warnings += "$($result.Path):$($result.LineNumber) - Found '$pattern'"
        }
    }
}

if (-not $brassFound) {
    Write-Host "  No brass colors found" -ForegroundColor Green
    $verified += "No brass colors"
} else {
    Write-Host "  Brass colors found (may be in comments or unused code)" -ForegroundColor Yellow
}

# Check 4: Old color system (text-ink, text-ink-muted)
Write-Host "Checking for old color system..." -ForegroundColor Yellow
$oldColorPatterns = @(
    "text-ink",
    "text-ink-muted",
    "bg-ink",
    "border-outline"
)

$oldColorsFound = $false
foreach ($pattern in $oldColorPatterns) {
    $results = Select-String -Path $projectFiles -Pattern $pattern -ErrorAction SilentlyContinue
    if ($results) {
        $oldColorsFound = $true
        foreach ($result in $results) {
            Write-Host "  Found '$pattern' in $($result.Path):$($result.LineNumber)" -ForegroundColor Yellow
            $warnings += "$($result.Path):$($result.LineNumber) - Found old color '$pattern'"
        }
    }
}

if (-not $oldColorsFound) {
    Write-Host "  No old color system found" -ForegroundColor Green
    $verified += "No old color system"
} else {
    Write-Host "  Old color system found (may need updating)" -ForegroundColor Yellow
}

# Check 5: Light backgrounds that should be dark
Write-Host "Checking for light backgrounds..." -ForegroundColor Yellow
$lightBgPatterns = @(
    "bg-white to-\[",
    "bg-white/80",
    "bg-white/70",
    "bg-white/40",
    "bg-gradient-to-b from-white"
)

$lightBgFound = $false
foreach ($pattern in $lightBgPatterns) {
    $escapedPattern = [regex]::Escape($pattern)
    $results = Select-String -Path $projectFiles -Pattern $escapedPattern -ErrorAction SilentlyContinue
    if ($results) {
        $lightBgFound = $true
        foreach ($result in $results) {
            Write-Host "  Found '$pattern' in $($result.Path):$($result.LineNumber)" -ForegroundColor Yellow
            $warnings += "$($result.Path):$($result.LineNumber) - Found light background '$pattern'"
        }
    }
}

if (-not $lightBgFound) {
    Write-Host "  No light backgrounds found" -ForegroundColor Green
    $verified += "No light backgrounds"
} else {
    Write-Host "  Light backgrounds found (may need updating)" -ForegroundColor Yellow
}

# Check 6: Verify key files exist
Write-Host "Checking key files..." -ForegroundColor Yellow
$keyFiles = @(
    "apps\web\src\components\brand\brand-logo.tsx",
    "apps\web\src\components\layout\navbar.tsx",
    "apps\web\src\components\layout\Sidebar.tsx",
    "apps\web\src\components\layout\footer.tsx",
    "apps\web\src\app\globals.css",
    "apps\web\src\app\page.tsx",
    "apps\web\src\app\pricing\page.tsx",
    "apps\web\src\app\(auth)\login\page.tsx",
    "apps\web\src\app\(auth)\register\page.tsx",
    "apps\web\src\app\(marketplace)\agents\page.tsx"
)

$missingFiles = @()
foreach ($file in $keyFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
        $verified += "File exists: $file"
    } else {
        Write-Host "  ❌ $file NOT found" -ForegroundColor Red
        $missingFiles += $file
        $issues += "Missing file: $file"
    }
}

# Check 7: Logo path in brand-logo.tsx
Write-Host "Checking logo path in brand-logo.tsx..." -ForegroundColor Yellow
$brandLogoPath = Join-Path $scriptRoot "apps\web\src\components\brand\brand-logo.tsx"
if (Test-Path $brandLogoPath) {
    $logoContent = Get-Content $brandLogoPath -Raw
    if ($logoContent -match "swarm-sync-logo\.png") {
        Write-Host "  Logo path correct" -ForegroundColor Green
        $verified += "Logo path correct"
    } else {
        Write-Host "  Logo path may be incorrect" -ForegroundColor Red
        $issues += "Logo path issue in brand-logo.tsx"
    }
} else {
    Write-Host "  brand-logo.tsx not found" -ForegroundColor Red
    $issues += "brand-logo.tsx file missing"
}

# Check 8: Dark theme classes in key files
Write-Host "Checking for dark theme classes..." -ForegroundColor Yellow
$darkThemePatterns = @(
    "bg-black",
    "text-white",
    "text-slate-400",
    "bg-white/5",
    "border-white/10"
)

$darkThemeFound = $false
$checkedFiles = @(
    "apps\web\src\app\page.tsx",
    "apps\web\src\app\pricing\page.tsx",
    "apps\web\src\components\layout\navbar.tsx"
)

foreach ($file in $checkedFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $foundInFile = $false
        foreach ($pattern in $darkThemePatterns) {
            if ($content -match [regex]::Escape($pattern)) {
                $foundInFile = $true
                $darkThemeFound = $true
                break
            }
        }
        if ($foundInFile) {
            Write-Host "  ✅ Dark theme classes found in $file" -ForegroundColor Green
            $verified += "Dark theme in $file"
        }
    }
}

# Summary
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verified Items: $($verified.Count)" -ForegroundColor Green
foreach ($item in $verified) {
    Write-Host "   - $item" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Warnings: $($warnings.Count)" -ForegroundColor Yellow
if ($warnings.Count -gt 0) {
    foreach ($warning in $warnings | Select-Object -First 10) {
        Write-Host "   - $warning" -ForegroundColor Gray
    }
    if ($warnings.Count -gt 10) {
        Write-Host "   ... and $($warnings.Count - 10) more" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Issues: $($issues.Count)" -ForegroundColor Red
if ($issues.Count -gt 0) {
    foreach ($issue in $issues) {
        Write-Host "   - $issue" -ForegroundColor Gray
    }
} else {
    Write-Host "   - No critical issues found!" -ForegroundColor Green
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan

# Save report
$newline = [Environment]::NewLine
$reportContent = "# Dark Theme Verification Report" + $newline
$reportContent += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" + $newline + $newline
$reportContent += "## Verified Items ($($verified.Count))" + $newline
$reportContent += ($verified -join $newline) + $newline + $newline
$reportContent += "## Warnings ($($warnings.Count))" + $newline
$reportContent += ($warnings -join $newline) + $newline + $newline
$reportContent += "## Issues ($($issues.Count))" + $newline
$reportContent += ($issues -join $newline) + $newline

$reportContent | Out-File -FilePath 'VERIFICATION-REPORT.md' -Encoding UTF8
Write-Host 'Report saved to VERIFICATION-REPORT.md' -ForegroundColor Cyan
Write-Host ''

if ($issues.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host 'All checks passed! Dark theme implementation looks good.' -ForegroundColor Green
    exit 0
} elseif ($issues.Count -eq 0) {
    Write-Host 'No critical issues found. Review warnings above.' -ForegroundColor Yellow
    exit 0
} else {
    Write-Host 'Critical issues found. Please review and fix.' -ForegroundColor Red
    exit 1
}


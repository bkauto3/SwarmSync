# PowerShell script to copy all agent files from Genesis to Agent-Market
# Run this from the Agent-Market root directory

$sourceAgents = "C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\agents"
$sourceInfra = "C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\infrastructure"
$dest = "C:\Users\Ben\Desktop\Github\Agent-Market\agents"

Write-Host "Copying agent files..." -ForegroundColor Cyan

# Copy all Python files from agents folder (except __init__.py)
$files = Get-ChildItem "$sourceAgents\*.py" -Exclude "__init__.py"
$copied = 0

foreach ($file in $files) {
    try {
        Copy-Item $file.FullName -Destination "$dest\$($file.Name)" -Force
        Write-Host "  ✓ Copied: $($file.Name)" -ForegroundColor Green
        $copied++
    } catch {
        Write-Host "  ✗ Failed: $($file.Name) - $_" -ForegroundColor Red
    }
}

# Copy business_idea_generator from infrastructure
try {
    $bizIdea = "$sourceInfra\business_idea_generator.py"
    if (Test-Path $bizIdea) {
        Copy-Item $bizIdea -Destination "$dest\business_idea_generator.py" -Force
        Write-Host "  ✓ Copied: business_idea_generator.py" -ForegroundColor Green
        $copied++
    } else {
        Write-Host "  ✗ Not found: business_idea_generator.py" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Failed: business_idea_generator.py - $_" -ForegroundColor Red
}

Write-Host "`nTotal files copied: $copied" -ForegroundColor Cyan
Write-Host "Done!" -ForegroundColor Green


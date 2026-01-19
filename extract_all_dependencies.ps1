# Extract dependencies for all agents from Genesis
$genesisDir = "C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis"
$agentMarketAgents = "C:\Users\Ben\Desktop\Github\Agent-Market\agents"
$extractScript = "$genesisDir\scripts\extract_agent.py"

$agents = @(
    "genesis_meta_agent",
    "builder_agent",
    "qa_agent",
    "spec_agent",
    "deploy_agent",
    "research_discovery_agent",
    "security_agent",
    "maintenance_agent",
    "seo_agent",
    "content_agent",
    "marketing_agent",
    "support_agent",
    "analyst_agent",
    "finance_agent",
    "pricing_agent",
    "email_agent",
    "billing_agent",
    "commerce_agent",
    "darwin_agent",
    "domain_name_agent",
    "legal_agent",
    "onboarding_agent",
    "reflection_agent",
    "waltzrl_conversation_agent",
    "waltzrl_feedback_agent",
    "se_darwin_agent",
    "ring1t_reasoning",
    "business_idea_generator"
)

Write-Host "🔍 Extracting dependencies for $($agents.Count) agents..." -ForegroundColor Cyan
Write-Host ""

$tempDir = "$agentMarketAgents\_extracted_temp"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$infraDir = "$agentMarketAgents\infrastructure"
New-Item -ItemType Directory -Force -Path $infraDir | Out-Null

$allInfraFiles = @{}

foreach ($agent in $agents) {
    Write-Host "📦 Extracting $agent..." -ForegroundColor Yellow
    $target = "$tempDir\$agent"
    
    $result = & python $extractScript $agent $target --source $genesisDir 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ $agent extracted successfully" -ForegroundColor Green
        
        # Collect infrastructure files
        $agentInfra = "$target\infrastructure"
        if (Test-Path $agentInfra) {
            $files = Get-ChildItem -Path $agentInfra -Filter "*.py" -File
            foreach ($file in $files) {
                if (-not $allInfraFiles.ContainsKey($file.Name)) {
                    $allInfraFiles[$file.Name] = $file.FullName
                }
            }
        }
    } else {
        Write-Host "   ⚠️  $agent extraction had issues" -ForegroundColor Yellow
        Write-Host "      $($result -join "`n      ")" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "📊 Found $($allInfraFiles.Count) unique infrastructure modules" -ForegroundColor Cyan
Write-Host "   Files: $($allInfraFiles.Keys -join ', ')" -ForegroundColor Gray

Write-Host ""
Write-Host "📂 Copying infrastructure files to $infraDir..." -ForegroundColor Cyan

foreach ($fileName in $allInfraFiles.Keys) {
    $sourceFile = $allInfraFiles[$fileName]
    $targetFile = "$infraDir\$fileName"
    
    if (-not (Test-Path $targetFile)) {
        Copy-Item -Path $sourceFile -Destination $targetFile -Force
        Write-Host "   ✅ Copied $fileName" -ForegroundColor Green
    } else {
        Write-Host "   ⏭️  Skipped $fileName (already exists)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "✅ Dependency extraction complete!" -ForegroundColor Green
Write-Host "   Infrastructure files in: $infraDir" -ForegroundColor Cyan


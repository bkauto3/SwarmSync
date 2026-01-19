# Extract all infrastructure modules needed by agents
$genesisInfra = "C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\infrastructure"
$agentMarketInfra = "C:\Users\Ben\Desktop\Github\Agent-Market\agents\infrastructure"

# Create infrastructure directory
New-Item -ItemType Directory -Force -Path $agentMarketInfra | Out-Null

# All unique infrastructure modules found from grep analysis
$infraModules = @(
    "load_env.py",
    "halo_router.py",
    "local_llm_client.py",
    "task_dag.py",
    "genesis_discord.py",
    "x402_client.py",
    "code_extractor.py",
    "business_monitor.py",
    "ap2_service.py",
    "genesis_discord_bot.py",
    "prompts.py",
    "llm_client.py",
    "hopx_agent_adapter.py",
    "x402_vendor_cache.py",
    "memory_os.py",
    "daao_router.py",
    "tumix_termination.py",
    "creative_asset_registry.py",
    "ocr",
    "deepseek_ocr_compressor.py",
    "self_correction.py",
    "openenv_wrapper.py",
    "env_learning_agent.py",
    "memory_os_mongodb_adapter.py",
    "memory",
    "ap2_connector.py",
    "namecom_client.py",
    "rifl.py",
    "reasoning_bank.py",
    "replay_buffer.py",
    "reflection_harness.py",
    "observability.py",
    "context_profiles.py",
    "hallucination_control.py",
    "trajectory_pool.py",
    "se_operators.py",
    "benchmark_runner.py",
    "security_utils.py",
    "casebank.py",
    "openhands_integration.py",
    "judge.py",
    "oracle_hgm.py",
    "safety_layer.py",
    "evolution",
    "safety"
)

Write-Host "📦 Copying infrastructure modules..." -ForegroundColor Cyan

$copied = 0
$skipped = 0
$errors = 0

foreach ($module in $infraModules) {
    $sourcePath = Join-Path $genesisInfra $module
    $targetPath = Join-Path $agentMarketInfra $module
    
    if (Test-Path $sourcePath) {
        try {
            if ((Get-Item $sourcePath).PSIsContainer) {
                # It's a directory - copy recursively
                if (-not (Test-Path $targetPath)) {
                    Copy-Item -Path $sourcePath -Destination $targetPath -Recurse -Force
                    Write-Host "   ✅ Copied directory: $module" -ForegroundColor Green
                    $copied++
                } else {
                    Write-Host "   ⏭️  Skipped directory (exists): $module" -ForegroundColor Gray
                    $skipped++
                }
            } else {
                # It's a file
                if (-not (Test-Path $targetPath)) {
                    Copy-Item -Path $sourcePath -Destination $targetPath -Force
                    Write-Host "   ✅ Copied: $module" -ForegroundColor Green
                    $copied++
                } else {
                    Write-Host "   ⏭️  Skipped (exists): $module" -ForegroundColor Gray
                    $skipped++
                }
            }
        } catch {
            Write-Host "   ❌ Error copying $module : $_" -ForegroundColor Red
            $errors++
        }
    } else {
        Write-Host "   ⚠️  Not found: $module" -ForegroundColor Yellow
    }
}

# Also copy __init__.py if it exists
$initFile = Join-Path $genesisInfra "__init__.py"
if (Test-Path $initFile) {
    $targetInit = Join-Path $agentMarketInfra "__init__.py"
    Copy-Item -Path $initFile -Destination $targetInit -Force
    Write-Host "   ✅ Copied: __init__.py" -ForegroundColor Green
}

Write-Host ""
Write-Host "📊 Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Copied: $copied" -ForegroundColor Green
Write-Host "   ⏭️  Skipped: $skipped" -ForegroundColor Gray
Write-Host "   ❌ Errors: $errors" -ForegroundColor $(if ($errors -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "✅ Infrastructure extraction complete!" -ForegroundColor Green
Write-Host "   Location: $agentMarketInfra" -ForegroundColor Cyan


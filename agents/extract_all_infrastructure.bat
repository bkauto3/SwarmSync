@echo off
REM Extract infrastructure dependencies for all agents

set GENESIS_DIR=C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis
set TARGET_DIR=C:\Users\Ben\Desktop\Github\Agent-Market\agents\infrastructure
set SCRIPT=%GENESIS_DIR%\scripts\extract_agent.py

echo Creating infrastructure directory...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo.
echo Extracting infrastructure dependencies for all agents...
echo.

REM Extract each agent to a temp directory, then consolidate infrastructure
for %%A in (
    genesis_meta_agent
    builder_agent
    qa_agent
    spec_agent
    deploy_agent
    research_discovery_agent
    security_agent
    maintenance_agent
    seo_agent
    content_agent
    marketing_agent
    support_agent
    analyst_agent
    finance_agent
    pricing_agent
    email_agent
    billing_agent
    commerce_agent
    darwin_agent
    domain_name_agent
    legal_agent
    onboarding_agent
    reflection_agent
    waltzrl_conversation_agent
    waltzrl_feedback_agent
    se_darwin_agent
    ring1t_reasoning
    business_idea_generator
) do (
    echo Extracting %%A...
    set TEMP_TARGET=%TARGET_DIR%\_temp_%%A
    python "%SCRIPT%" %%A "%TEMP_TARGET%" --source "%GENESIS_DIR%"
    
    REM Copy infrastructure files from temp to main infrastructure
    if exist "%TEMP_TARGET%\infrastructure" (
        echo   Copying infrastructure files for %%A...
        xcopy "%TEMP_TARGET%\infrastructure\*" "%TARGET_DIR%\" /E /I /Y >nul
    )
    
    REM Clean up temp directory
    if exist "%TEMP_TARGET%" rmdir /S /Q "%TEMP_TARGET%"
)

echo.
echo Infrastructure extraction complete!
echo Files are in: %TARGET_DIR%
pause


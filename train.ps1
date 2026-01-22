# Training script for agent optimization
# Usage: .\train.ps1 [horizon] [iters] [pop]
# Defaults: horizon=400, iters=3, pop=6

param(
    [int]$Horizon = 400,
    [int]$Iters = 3,
    [int]$Pop = 6
)

$env:PYTHONIOENCODING = "utf-8"
$env:POLICY_FILE = "policy.signa"
$env:TARGET_RESOURCE_PREFIXES = [char]::ConvertFromUtf32(0x1F451) + "," + [char]::ConvertFromUtf32(0x1F4B0)  # 👑,💰
$env:AGENT_BATCH = "4096"
$env:CEM_TRAIN_BATCH = "2048"
$env:CEM_TRAIN_HORIZON = "100"
$env:CEM_EVAL_EVERY = "20"
$env:CEM_OBJECTIVE = "max"
$env:CEM_POP = $Pop
$env:CEM_ITERS = $Iters
$env:AGENT_HORIZON = $Horizon
$env:DECISION_ONLY = "1"
$env:PHYSICS_BURST_MAX = "128"
$env:FINAL_HEARTBEAT_EVERY = "100"

Write-Host "Running training: horizon=$Horizon iters=$Iters pop=$Pop"
Write-Host "Target prefixes: $env:TARGET_RESOURCE_PREFIXES"

& "G:/LOKI/LOCUS/SIGNUM/signamancy/.venv/Scripts/python.exe" -X utf8 -m signamancy.agent.run_agent_generic

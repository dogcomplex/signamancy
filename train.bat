@echo off
REM Training script for agent optimization
REM Usage: train.bat [horizon] [iters] [pop]
REM Defaults: horizon=400, iters=3, pop=6

setlocal

set HORIZON=%1
if "%HORIZON%"=="" set HORIZON=400

set ITERS=%2
if "%ITERS%"=="" set ITERS=3

set POP=%3
if "%POP%"=="" set POP=6

set PYTHONIOENCODING=utf-8
set POLICY_FILE=policy.signa
set TARGET_RESOURCE_PREFIXES=👑,💰
set AGENT_BATCH=4096
set CEM_TRAIN_BATCH=2048
set CEM_TRAIN_HORIZON=100
set CEM_EVAL_EVERY=20
set CEM_OBJECTIVE=max
set CEM_POP=%POP%
set CEM_ITERS=%ITERS%
set AGENT_HORIZON=%HORIZON%
set DECISION_ONLY=1
set PHYSICS_BURST_MAX=128
set FINAL_HEARTBEAT_EVERY=100

echo Running training: horizon=%HORIZON% iters=%ITERS% pop=%POP%
"G:/LOKI/LOCUS/SIGNUM/signamancy/.venv/Scripts/python.exe" -X utf8 -m signamancy.agent.run_agent_generic

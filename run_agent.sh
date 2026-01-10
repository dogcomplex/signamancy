#!/bin/bash
# Wrapper script to run agent with config from agent_config.env
cd "C:/Users/devil/.claude-worktrees/signamancy/charming-mahavira"

# Source config file if it exists
if [ -f agent_config.env ]; then
    export $(grep -v '^#' agent_config.env | xargs)
fi

# Run the agent
"G:/LOKI/LOCUS/SIGNUM/signamancy/.venv/Scripts/python.exe" -X utf8 -m signamancy.agent.run_agent_generic "$@"

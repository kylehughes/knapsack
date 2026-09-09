## Check that installed coding agents use the shared Knapsack configuration.
check/agents:
	@bash "./scripts/check-agents.sh"

## Run agent-configuration checker tests.
test/agents:
	@bash "./scripts/tests/test-claude-settings.sh"
	@bash "./scripts/tests/test-check-agents.sh"

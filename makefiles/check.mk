## Check that installed coding agents use the shared Knapsack configuration.
check/agents:
	@bash "./scripts/check-agents.sh"

## Check Codex routing installation and hook eligibility without model calls.
check/codex-routing:
	@python3 "./scripts/check-codex-routing.py"

## Run agent-configuration checker tests.
test/agents:
	@bash "./scripts/tests/test-claude-settings.sh"
	@bash "./scripts/tests/test-check-agents.sh"
	@python3 "./scripts/tests/test-codex-routing.py"
	@python3 "./scripts/tests/test-codex-routing-status.py"
	@python3 "./scripts/tests/test-set-up-codex-routing.py"

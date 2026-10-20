## Preview dotfile installation actions without changing local state.
plan/dotfiles:
	@python3 -B "./scripts/manage-dotfiles.py" plan

## Check installed dotfile copies, ownership, and isolation.
check/dotfiles:
	@python3 -B "./scripts/manage-dotfiles.py" check

## Check shared sources and run isolated fixture tests.
check/repository:
	@python3 -B "./scripts/check-repository.py"
	@$(MAKE) test/dotfiles test/agents

## Run isolated dotfile installation and source-policy tests.
test/dotfiles:
	@python3 -B "./scripts/tests/test-dotfile-composition.py"
	@python3 -B "./scripts/tests/test-manage-dotfiles.py"
	@python3 -B "./scripts/tests/test-two-mac-migration.py"
	@python3 -B "./scripts/tests/test-repository-checks.py"

## Check that installed coding agents use the shared Knapsack configuration.
check/agents:
	@bash "./scripts/check-agents.sh"

## Check Codex routing installation and hook eligibility without model calls.
check/codex-routing:
	@python3 -B "./scripts/check-codex-routing.py"

## Run agent-configuration checker tests.
test/agents:
	@bash "./scripts/tests/test-claude-settings.sh"
	@bash "./scripts/tests/test-check-agents.sh"
	@python3 -B "./scripts/tests/test-codex-routing.py"
	@python3 -B "./scripts/tests/test-codex-routing-status.py"
	@python3 -B "./scripts/tests/test-set-up-codex-routing.py"

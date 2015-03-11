# Knapsack by Kyle Hughes

## Installation

1. Clone the repository to your home (`~/`) directory.
2. Pull down the submodules:

		git submodule init
		git submodule update
		
3. Setup symlinks.

## Dependencies

Dependency management is done using `subtree` instead of `submodule`. All dependencies are stored in 
`dotfiles/_/[dependency_name]`.

The dependencies for this project are:  
- [tmuxifier][dependencies_tmuxifier]


[dependencies_subtree_explain]: http://blogs.atlassian.com/2013/05/alternatives-to-git-submodule-git-subtree/
[dependencies_tmuxifier]: https://github.com/jimeh/tmuxifier

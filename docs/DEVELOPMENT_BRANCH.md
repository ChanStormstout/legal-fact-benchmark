# Development branch: rules and decisions

This document records the branch setup and its historical publication policy. It does
not grant new publication or experiment authorization.

The development branch is `research/rules-and-verdict`, created from
`9ddc35d0a3b4b60fde11b3f669139ed38469aac3`. That starting point included the published
code, historical experiments, and the revised research objective. Creating the branch
did not change the default branch or merge its work into `main`.

The research reuses sources, extraction, field dependencies, and relation execution
while investigating rule acquisition, applicable-authority retrieval, and claim-level
reasoning. New methods and experiments use new version directories. Original
annotations, failures, frozen configurations, and method snapshots remain intact.
The branch setup itself did not run models, add annotations, or implement a new legal
reasoning algorithm.

## Local work and publication

On 2026-10-02, the user authorized publication after completed experiments once reports,
state, review artifacts, and the publication manifest were checked. That historical
authorization included the then-current V7. Later task-specific instructions to withhold
publication take precedence. An older report's statement that it was not pushed records
its status at the time; later publication does not rewrite that evidence.

The registered target is in `repository-artifacts.json`. Local preparation is:

```sh
python3 scripts/repository_bridge.py prepare
python3 scripts/repository_bridge.py verify
```

The separate `sync --message ...` command commits and pushes only after confirming
that the current branch and repository match the registered target. It does not
implicitly push to `main`. Register new output roots and inspect the publication
manifest first. Environments, weights, browser captures, credentials, and unregistered
local data are excluded.

Multiple chats using the same checkout see the same files and branch. Use separate
Git worktrees when work genuinely requires different branches. The original branch
setup did not create a second worktree. The incomplete `legal_bench/local_chunk_v11.py`
was kept local and excluded from publication.

## Review the intended revision

Share the [registered review entry](https://github.com/ChanStormstout/legal-fact-benchmark/blob/research/rules-and-verdict/review/START_HERE.md)
and specify the branch and snapshot identifier. Replace the branch with a published
commit SHA when fixing a review revision. If GitHub cannot provide complete files,
upload the Markdown volumes or exported package from the same snapshot.

Accepting review suggestions, starting experiments, changing methods, and merging to
`main` remain subject to the active task's authorization and freeze requirements.

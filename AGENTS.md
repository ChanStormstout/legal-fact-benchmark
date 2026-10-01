# Repository working agreement

Read README.md, docs/PROJECT_STATE.json and review/START_HERE.md first.

Preserve original annotations, sources, failed outputs, frozen configurations and
historical method snapshots. Changed methods/results use a new versioned output
directory. Do not overwrite a completed experiment to make it agree with a reference.

Reference labels are model-generated and source-reviewed, not human gold. Distinguish
program tests, source checks, model-reference agreement and independently evaluated
capabilities. Technical failures have a null answer; UNKNOWN is an answer, not a
substitute for failure. Do not turn a failed pair into whole-case absence.

The completed Qwen v3 round is development validation after observed format failures.
No new model runs, annotation or semantic fixes are authorized merely by a review.
Use project-local MLX dependencies; never commit environments or model weights.

After an authorized change, update docs/CHANGELOG.md and the experiment catalog if
needed. Run `python3 scripts/repository_bridge.py prepare`, inspect its publication
manifest, and use `verify`. `sync --message ...` explicitly stages the allowlisted
files, commits and pushes. Ordinary local work is not automatically published.

Do not stage browser UI captures, credentials, unrelated local data, third-party
paper PDFs, or bulk datasets. New output roots require explicit registration in
docs/repository-artifacts.json. Preserve frozen file bytes even if they contain
historical machine-specific paths; document portability instead of rewriting them.

Use concise Chinese paragraphs for Chinese user updates; explain concrete causes
and distinguish completed, verified and blocked work.

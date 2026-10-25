# Reviewing the project with ChatGPT

Git stores traceable versions. A reviewer reads a specified snapshot and returns
findings; an authorized development task decides whether to implement them. Browser
conversations are not automatically synchronized into this repository. Preparing a
review package neither launches experiments nor commits or pushes changes.

## Share a specific snapshot

Start with [review/START_HERE.md](../review/START_HERE.md) and
[review/REVIEW_REQUEST.md](../review/REVIEW_REQUEST.md). The registered review branch
is `research/rules-and-verdict`. Specify both the branch and the snapshot identifier;
for a fixed published revision, replace the branch in a GitHub URL with its commit SHA.
A repository homepage alone may show a different branch or older publication.

Ask the reviewer to distinguish full-file reading, summary-only reading, and inaccessible
links. A file that was not retrieved cannot be claimed as reviewed. If repository
access is unavailable, share accessible raw links or upload the matching Markdown
review files. `python3 scripts/repository_bridge.py export` creates a local ZIP; whether
a particular chat can read that ZIP depends on its available tools.

## Read the right evidence

`review/CODE.md` contains selected source code. `review/RESULTS.md` contains the selected
report. `review/MANIFEST.json` records the snapshot and file hashes. The historical
`SOURCES_*.md` volumes belong to earlier relation experiments and are not automatically
the sources for a later run. Use the selected protocol and its actual source records;
quoted snippets in a results summary do not replace the underlying material.

Feedback should identify the issue, file or line, supporting evidence, proposed change,
and appropriate validation. The structured format is in
[review/feedback/schema.json](../review/feedback/schema.json). Save replies unchanged
when they are used as review evidence. Suggestions are not automatically accepted,
implemented, or posted to GitHub.

## Update locally, publish only when authorized

After an authorized change, update the relevant documentation and catalog, then run:

```sh
python3 scripts/repository_bridge.py prepare
python3 scripts/repository_bridge.py verify
```

Inspect `review/PUBLICATION.json` before any publication. The separate `sync` command
stages allowlisted files, commits, and pushes; it requires applicable publication
authorization and is not part of ordinary documentation editing. It checks the registered
repository and branch and refuses unrelated staged files. A failed push is not permission
to force-push, roll back, or overwrite a remote branch. Frozen experiment requirements
continue to apply.

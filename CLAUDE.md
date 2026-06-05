# Claude guidelines for this project

## Code comments
All code must be carefully commented. Comments explain *why*, not what:
- Business rules and domain logic (e.g. why a symbol is forbidden, why a field has a length limit)
- Non-obvious design decisions
- Any workaround or constraint that would surprise a reader

Short functions with self-explanatory names do not need a comment. Long or complex
functions get a docstring. Never describe what the code literally does — only what
a reader could not deduce from the code itself.

## Reviewing together before publishing
Go through code together with the user before any git push. The user must confirm
explicitly that the code is ready to publish. "The changes look good" is not
confirmation enough — wait for a clear "ok to push" or equivalent.

## Confirming before bigger changes
Before making larger changes (refactoring a module, changing data structures,
rewriting a function in a substantially different way), describe the plan first
and wait for the user to agree. Small fixes and typo corrections can be done
directly.

## Git push
Never push to the remote repository unless the user explicitly says to push.
A request to commit does not imply a request to push.
When ready to push, state clearly what will be pushed and ask for confirmation.

**Summary:** This prompt runs a reusable "PR conflict radar" for a GitHub repo. Given one author ({AUTHOR}), it finds every *other* author's newer open PR that would actually merge-conflict with one of {AUTHOR}'s open PRs — verified with a real `git merge-tree` 3-way merge, not just file-name overlap (which is noise in a repo full of monolithic files). It ranks conflicts by severity, then stops and reports. Public heads-up comments are strictly opt-in and reserved for *major* overlaps only, gated behind your explicit approval.

**Variables (fill these in, then paste the prompt body below as-is):**
- `{AUTHOR}` `theoryshaw`
- `{REPO}` `IfcOpenShell/IfcOpenShell`
- `{BASE}` `v0.8.0`
- `{SKIP_AUTHORS}` → *(optional)* comma-separated logins already analyzed, to skip (e.g. `BimVoice`)

---

> **PR conflict analysis — {REPO}**
>
> Find open PRs by **any author** that will merge-conflict with open PRs by **{AUTHOR}**. Constraints:
> - Only where the **other author's PR is newer** than {AUTHOR}'s (compare `createdAt`).
> - **Exclude drafts** on both sides.
> - Exclude {AUTHOR}'s own PRs from the "other" side. (Optionally skip authors already analyzed, e.g. `{SKIP_AUTHORS}`.)
>
> Method (don't shortcut it — file-level overlap alone is far too noisy because Bonsai has monolithic `operator.py`/`ui.py`/`prop.py`/`tool.py` files touched by dozens of PRs):
> 1. Pull **all** open PRs via `gh pr list --repo {REPO} --state open --json number,title,author,createdAt,isDraft --limit 2000`. Split into {AUTHOR}'s non-draft PRs vs everyone else's non-draft PRs. Report the author breakdown (`Counter` of logins) so the scope is visible.
> 2. Get each PR's changed files (batched GraphQL `pullRequest(number:){files}` — ~25 per query, with retries; the endpoint occasionally returns `unexpected EOF`). Find pairs sharing files, respecting the newer-than + non-draft filters.
> 3. **Verify every candidate with a real 3-way merge**: fetch both PR heads into a local clone of {REPO} (`git fetch origin +refs/pull/N/head:refs/prs/N`, only the ones not already fetched) and run `git merge-tree --write-tree --name-only refs/prs/OTHER refs/prs/AUTHOR_PR`. Exit code 1 = real conflict; keep only these. (This dropped most false positives for us — 51 candidates → 7 real.)
> 4. Quantify severity: read the conflicted blob from the written tree (`git cat-file -p <tree>:<path>`) and count `<<<<<<<`…`>>>>>>>` regions and lines. Distinguish **semantic** overlaps (both PRs change the same feature) from incidental adjacency, and de-prioritize sweeping "refactor everything" PRs that conflict with everything and are unlikely to merge.
> 5. Report grouped by {AUTHOR}'s PR, most-conflicts first, with clickable PR links, the other author's login, and exact conflicting file paths + region/line counts.
>
> **Then present the findings and STOP. Do not post anything automatically.**
>
> **Posting a comment is the exception, not the default — reserve it for MAJOR overlaps only.** Most conflicts are minor line-adjacency that git or a quick rebase resolves trivially; commenting on those is noise and must be skipped. A conflict qualifies as "major" **only if all of these hold**:
> - it's a **semantic** overlap — both PRs are reworking the **same feature/logic**, not just editing nearby lines in a big shared file;
> - the conflict is **substantial** — many lines / multiple regions, i.e. real hand-resolution work, not a one-liner;
> - it's a **realistic merge candidate** — not a sprawling "modernize everything" PR that conflicts with the whole repo and is unlikely to land.
>
> When in doubt, **don't comment.** It's better to under-flag than to spam authors. Ask me before posting, and list exactly which pairs you consider major and why — I make the final call.
>
> If (and only if) I approve: verify `gh auth status` is the intended account first. **Then, before posting, check that PR for an existing heads-up** — pull its comments (`gh pr view N --repo {REPO} --json comments`) and skip any PR that already has a conflict heads-up **from any account** (not just the authenticated one — match on conflict/heads-up wording like "Just a heads up", "merge conflict", `git merge-tree`, or a link to the same {AUTHOR} PR). If someone else already flagged the same collision, don't pile on. No need to ping a PR twice; if a prior note from *our own* account is now stale (different files/counts), edit it (`gh pr comment N --edit-last`) rather than adding a new one — but leave other people's comments alone. Post this template on the **other author's** PR, linking {AUTHOR}'s PR (reference multiple {AUTHOR} PRs in one comment if the same PR conflicts with several):
>
> > Hi, Just a heads up — this PR overlaps with #{AUTHOR_PR} (*{title}*), and on top of `{BASE}` the two **don't auto-merge** (verified with `git merge-tree`). It's a significant overlap: the merge leaves **{N regions / ~M lines}** to resolve by hand in `{files}`. Nothing's broken while both are open — but whichever lands second will need a manual rebase, so flagging early to coordinate. 🙂

---

**Gotchas baked in from the session that produced this prompt:**
- Strip `\r` from any Windows-written ref lists before feeding refspecs to git (a stray CR produces `invalid refspec`).
- `merge-tree --name-only` gives basenames-in-context — read the tree blob for the **full** path before quoting it in a comment.
- Retry the GraphQL file-fetch on `unexpected EOF`.
- Merge against the PRs' actual base branch (`{BASE}`) — for IfcOpenShell that's `v0.8.0`, not `main`.

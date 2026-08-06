# Standing up a curated BonsaiPR instance

How to run your own BonsaiPR that builds *your* curation rather than every open
PR — which is what makes you a distinct publisher under
[RFC-001](../../proposals/RFC-001-federated-curated-builds.md) instead of a
second copy of the canonical answer.

The canonical instance at `falken10vdl/bonsaiPR` builds all ~847 open PRs. A
curated instance builds only what its profile selects. Two builds of *everything*
agree trivially and tell you nothing; two builds of different curations that
agree about a PR is evidence.

---

## 1. What you need

| | |
|---|---|
| A fork of `bonsaiPR` | where the workflow runs, and where reports and releases are published |
| A fork of `IfcOpenShell` | receives the **force-pushed** build branch |
| A profile in `profiles/` | your curation |
| A PAT | pushes to a *second* repo, so the built-in `GITHUB_TOKEN` is not enough |

### The fork warning

The build branch is pushed with `--force`. `FORK_OWNER`/`FORK_REPO` must name a
fork you own and do not do other work in. `BASE_CLONE_DIR` is likewise checked
out, reset, and branch-deleted — on a runner that is a scratch directory, but if
you ever run this locally, **never point it at a repository you work in**.

---

## 2. Getting a profile

If you already maintain a build branch by hand, distil it rather than writing
one:

```bash
cd automation/scripts
python distill.py profile \
  --branch  Ryan_build-0.8.6-alpha2607071335 \
  --repo    /path/to/your/IfcOpenShell \
  --name    openingdesign \
  --maintainer OpeningDesign
```

That writes `profiles/<name>.json` and `profiles/<name>.provenance.json`. Read
the provenance file before trusting the profile — it records how every commit
was attributed and with what confidence.

Otherwise, copy `profiles/example-curated.json`, rename it, and replace the
contents. Validate with:

```bash
python bonsaipr_profile.py check <name>
```

---

## 3. Repository configuration

**Secret** (Settings → Secrets and variables → Actions → Secrets):

| name | value |
|---|---|
| `BONSAIPR_TOKEN` | PAT with `repo` scope, able to push to **both** forks and create releases |

**Variables** (same page → Variables). All optional; the defaults are the
`OpeningDesign` ones:

| name | default |
|---|---|
| `BONSAIPR_OWNER` | `OpeningDesign` |
| `BONSAIPR_REPO` | `bonsaiPR` |
| `BONSAIPR_FORK_OWNER` | `OpeningDesign` |
| `BONSAIPR_FORK_REPO` | `IfcOpenShell` |

A fine-grained PAT needs, on both forks: *Contents: read and write*. On the
release target it also needs *Contents: read and write* for the release upload.

---

## 4. First run

Actions → **Curated build** → *Run workflow*. Pick your profile and start with
**`manifest-only`**.

`manifest-only` runs stage 0 only: clone, merge the profile's PRs, and write the
report plus `state.<order>.json` and `rivals.<order>.json`. That is *everything
federation consumes* — stages 1–2 only add installable zips and a GitHub
release. It is also much faster, so it is the honest way to find out whether
your profile merges at all before spending an hour on packaging.

Once that succeeds, run again with `full`.

The schedule is commented out in the workflow. Enable it only after a manual run
has worked end to end.

---

## 5. What to expect

- **Time is dominated by fetching**, not merging: each PR comes from a different
  contributor's fork, so a 160-PR profile does 160 fetches from 160 remotes.
- **A single-order profile builds once.** If `orders` names one order, `main.py`
  skips the descending / by-updated retries — a selective profile usually has
  few internal conflicts, so three near-identical builds would be wasted.
- **Selected PRs that closed are reported, not silently dropped.** Stage 0 prints
  which of your selected PRs are no longer open. That is your signal that the
  profile has drifted and wants regenerating.
- **Disk is the likeliest failure.** The workflow reclaims ~20 GB before
  starting; if a `full` run still fails on space, use `manifest-only`, which
  needs far less.

---

## 6. Joining the federation

Once your instance publishes reports, others add you to their `peers.json` and
your curation starts contributing to the aggregate. Your reports are already at
a stable public URL by virtue of being committed:

```
https://raw.githubusercontent.com/<owner>/bonsaiPR/main/automation/reports/
```

Aggregate locally at any time with:

```bash
cd automation/scripts && python federate.py digest
```

Cross-publisher aggregation is RFC-001 phase 2 and is not built yet — this is
the half that has to exist first, since there is nothing to federate until a
second real curation is publishing.

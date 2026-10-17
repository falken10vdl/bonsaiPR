# BonsaiPR, end to end

Two walkthroughs. **Part 1** is for someone who wants to *install* a curated
build — five minutes, no accounts, nothing to build. **Part 2** is for someone
who wants to *publish* one.

If you are reading this to decide whether it is worth your time, read
[§0](#0-two-roles) and [§4](#4-what-this-does-not-do) first. §4 is where the
limits are, including one that will matter to anyone carrying C++ changes.

---

## <a id="0-two-roles"></a>0. Two roles

A **curator** decides which open pull requests belong together, builds them into
one add-on, and publishes the result. A **subscriber** installs that result.

| | curator | subscriber |
|---|---|---|
| needs a GitHub account | yes | no |
| builds anything | yes, in CI | no |
| chooses which PRs | yes | no — you take the curation as offered |
| publishes | a release, a feed, and a manifest | nothing |

Three things follow, and they are the questions people ask first:

- **Subscribers do not build.** You install a zip the curator already built.
- **A subscriber becomes a curator** by forking this repo, adding a profile, and
  running the workflow. Nothing else changes hands.
- **The only real difference is publishing** — and specifically publishing a
  *manifest*, not just a config. A profile says what you intended to build; a
  manifest records what actually happened: which PRs merged, at which commits,
  which conflicted. The config is an opinion. The manifest is evidence.

---

## 1. Subscriber

### 1.1 Add the feed

In Blender: **Edit → Preferences → Get Extensions**, then the **⌄** menu at the
top right → **Add Remote Repository**. Paste a curator's feed URL:

```
https://raw.githubusercontent.com/OpeningDesign/bonsaiPR/main/profiles/openingdesign/index.json
```

Tick **Check for Updates on Startup**, then **Add**. The curation appears as its
own repository in the extensions list.

### 1.2 Install

Find the add-on under that repository and install it. Blender picks the build
matching your platform and Python version automatically — a Blender 4.x install
takes the `py311` build, Blender 5.1 takes `py313`.

**Disable any existing Bonsai extension first.** Both occupy the same module
name, and running the two together produces import errors that look like build
failures.

### 1.3 Read the report

Every build publishes a report listing exactly what went into it. For a release
it is attached to the release and archived in the repo under
`automation/reports/archive/`.

Two things in it are worth understanding:

- **📌** — this PR was built at an *earlier* commit than its current head,
  because the head no longer merges. The build fell back to the last commit the
  curator had validated. You are running a slightly older version of that PR.
- **Behind head** — how much of that PR's own new work you are missing. `0` means
  the branch was rewritten but nothing changed in substance. A large number means
  that PR has moved on substantially since the curator last validated it.

Neither is a defect. They are the build telling you where it is approximate.

---

## 2. Curator

### 2.1 Fork two repositories

| fork | why |
|---|---|
| `bonsaiPR` | where the workflow runs and where releases are published |
| `IfcOpenShell` | receives the **force-pushed** build branch |

The IfcOpenShell fork must be one you do not work in — the build branch is
force-pushed, and local branches there are reset and deleted.

### <a id="22-write-a-profile"></a>2.2 Write a profile

A profile is a list of PR numbers with a base. If you already keep that list in a
text file, you already have a profile; it just needs to be JSON.

```json
{
  "schema": 1,
  "name": "mycuration",
  "maintainer": "yourname",
  "base": { "repo": "IfcOpenShell/IfcOpenShell", "branch": "v0.8.0" },
  "select": { "mode": "allowlist", "prs": [8760, 9330, 8847, 8587] }
}
```

Save it as `profiles/mycuration.json`. Omit `base.commit` to follow the branch
tip; add it later when you want to pin (see [§3](#3-living-with-it)).

**If you already maintain a build branch**, distil the profile out of it rather
than writing one:

```bash
cd automation/scripts
curl -O https://raw.githubusercontent.com/falken10vdl/bonsaiPR/main/automation/reports/state.asc.json
python distill.py profile \
  --branch    integration \
  --repo      /path/to/your/IfcOpenShell \
  --name      mycuration \
  --pr-index  ./state.asc.json
```

`--pr-index` is the pipeline's snapshot of open PRs — number, title, author,
branch. Without it distill still runs, but every attribution loses its title and
author and one matching rung is silently disabled, so it will tell you loudly
that it is missing. Running `distill.py` from inside a `bonsaiPR` clone finds it
automatically; the default path is relative to the script, not to your shell.

For better attribution, mirror the PR refs first. This is what lets distill tell
a commit you cherry-picked off someone's PR from work that is genuinely yours:

```bash
git fetch origin "+refs/pull/*/head:refs/remotes/pr/*"
```

Read `mycuration.provenance.json` before trusting the profile. It records how
every commit was attributed and with what confidence.

### 2.3 Validate

```bash
python bonsaipr_profile.py check mycuration
```

Fix anything it reports before running a build.

### 2.4 Configure the repository

**Secret** — Settings → Secrets and variables → Actions:

| name | value |
|---|---|
| `BONSAIPR_TOKEN` | PAT with *Contents: read and write* on **both** forks |

**Variables** — same page:

| name | set to |
|---|---|
| `BONSAIPR_DEFAULT_PROFILE` | `mycuration` |
| `BONSAIPR_OWNER` / `BONSAIPR_REPO` | your bonsaiPR fork |
| `BONSAIPR_FORK_OWNER` / `BONSAIPR_FORK_REPO` | your IfcOpenShell fork |

### 2.5 First run: `manifest-only`

Actions → **Curated build** → *Run workflow* → `stages: manifest-only`.

A few minutes, no packaging, no release. It answers the only question that
matters at this stage: **does my curation still build?** Read the report before
going further — the PRs under *Conflict With Other PRs* are your real work queue.

### 2.6 Then `full`

Same workflow, `stages: full`. Adds seven platform zips (4 × py311 for Blender
4.x, 3 × py313 for Blender 5.1 — no Intel macOS), a GitHub release, the feed, and
a permanently archived report.

Note the asymmetry: **`manifest-only` reports expire in 14 days.** Only `full`
runs leave a permanent record.

### 2.7 Publish the URL

Your feed is:

```
https://raw.githubusercontent.com/<owner>/bonsaiPR/main/profiles/<name>/index.json
```

Hand that to anyone. They are now at [Part 1](#1-subscriber).

---

## <a id="3-living-with-it"></a>3. Living with it

**Nothing runs on a timer.** Every build is started by hand, deliberately. You
build when you have a reason to, and the record then reflects what you actually
experienced rather than what a 3am cron run happened to see.

**Pins are a fallback, not a freeze.** Each run tries every PR at its current
head first. Only when that fails does it fall back to the last commit you
validated, and the report says so with 📌. You do not maintain pins; they
maintain themselves.

**Advancing a pin is unilateral.** Re-pinning happens inside *your* profile, so
you can advance a pin on someone else's PR without asking them. Rebasing their
branch, you cannot. That asymmetry is worth remembering when a PR drifts.

**Deciding when to advance the base** uses two modes that answer different
questions:

```bash
python base_advisor.py --profile mycuration --repo /path/to/IfcOpenShell
python base_advisor.py --profile mycuration --repo /path/to/IfcOpenShell --in-stack
```

The default merges each PR onto the base *alone*. `--in-stack` replays the whole
curation in order, each PR onto the result of the last — which is what the build
does. A PR can merge onto every candidate base perfectly and still need a pin
because it collides with a PR merged before it, and the default mode cannot see
that at all. **Decide on `--in-stack`.**

**Base and pins move together.** Advancing the base while leaving PRs pinned at
old commits — or the reverse — measures worse than doing neither. When you
advance, advance both, which in practice means composing a fresh build branch and
re-distilling from it.

---

## <a id="4-what-this-does-not-do"></a>4. What this does not do

**C++ is never recompiled.** BonsaiPR ships the Python add-on against a pinned,
prebuilt `ifcopenshell` wheel. A PR that changes compiled C++ will merge, and its
Python will be packaged, but the C++ has no effect — the add-on either crashes at
runtime or silently runs the old wheel's behaviour.

This is the most important limitation here. If your curation exists to test a C++
change, BonsaiPR will hand you a build that looks correct and is not testing your
change. Set `"exclude": { "cpp": true }` to drop such PRs rather than carry them
misleadingly, or build them with a toolchain that compiles.

**Closed PRs stay in your profile until you remove them.** `refs/pull/<n>/head`
keeps resolving after a PR closes, so a closed PR is not an error — it is simply
never built. Stage 0 reports which of your selected PRs are no longer open.

**A curation is a snapshot.** It describes your thinking when you distilled it.
It does not follow you.

---

## 5. When it goes wrong

| symptom | cause | fix |
|---|---|---|
| every PR shows `"not in PR index"` | distill run outside a bonsaiPR clone, so the default index path resolved to nothing | pass `--pr-index`, per [§2.2](#22-write-a-profile) |
| `residue (UNVERIFIED)` in a distill report | no PR refs mirrored, so cherry-picks cannot be told from your own work | `git fetch origin "+refs/pull/*/head:refs/remotes/pr/*"` |
| every attribution says `probable` | your merge subjects do not name the PR in a form the ladder recognises | subjects starting `Merge PR #<n>` match exactly; otherwise read the provenance file |
| build fails naming failed targets | a platform did not build | it refuses to publish a partial release; fix the target, or set `BONSAIPR_ALLOW_PARTIAL_BUILD=1` deliberately |
| `full` run fails on disk space | packaging needs room | use `manifest-only`, which needs far less |
| a PR you selected never appears | it closed | remove it from `select.prs` |

---

## Where to go next

- [`.github/workflows/README-curated-build.md`](../.github/workflows/README-curated-build.md) — the operator reference, in more depth than this
- [`proposals/RFC-001-federated-curated-builds_plain-language.md`](../proposals/RFC-001-federated-curated-builds_plain-language.md) — why any of this exists, without jargon
- [`proposals/RFC-001-federated-curated-builds.md`](../proposals/RFC-001-federated-curated-builds.md) — the design, the measurements, and what is still unresolved

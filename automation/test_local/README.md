# Local test rig for the bonsaiPR release/report pipeline

A **scoped** harness that runs the real upload/report scripts against a throwaway
GitHub repo, driven by a synthetic report + fake addon zips — so you can validate
release-body / delta / reports changes in seconds, **without** cloning
IfcOpenShell or building Blender addons.

It exercises exactly the code that changes most often:
`02_upload_to_falken10vdl.py`, `pr_state.py`, `commit_reports.py`.

## What it proves

- The release body is generated correctly (build stats, downloads, the
  **🔁 Changes since last build** delta, the **📄 Full per-PR breakdown** link,
  contributors) and stays well under GitHub's size limit.
- The run-to-run **delta** is right: added / now-merging / newly-failing /
  updated / dropped PRs, plus the `events.*.jsonl` log.
- `commit_reports.py` commits and pushes `automation/reports/` to the repo.
- Release assets (zips + README report) upload and the README link resolves.

## Isolation (why it's safe)

Everything runs inside a **sandbox** = a fresh clone of the test repo with the
current `automation/` scripts copied in. The real scripts derive their paths
(`REPORTS_DIR`, `index.json`, the git repo they push) from `__file__`, so running
the copies inside the sandbox keeps your real working tree untouched. Report and
build fixtures live **outside** the sandbox, so they're never committed. All
runtime artifacts live under `RIG_ROOT` (default `~/bonsaiPR_testrig`), **outside**
the Dropbox-synced repo (a venv inside Dropbox corrupts).

## Prerequisites

- `gh` authenticated (`gh auth status`) with `repo` scope — used for the token
  and for cloning/pushing the test repo.
- A test repo under your account (default `theoryshaw/bonsaiPR-testbed`, public so
  asset links resolve anonymously). Create once:
  ```bash
  gh repo create <you>/bonsaiPR-testbed --public --add-readme
  ```
- A venv with `requests` + `python-dotenv`, created **outside** Dropbox:
  ```bash
  RIG="$HOME/bonsaiPR_testrig"
  python -m venv "$RIG/.venv"
  "$RIG/.venv/Scripts/python.exe" -m pip install requests python-dotenv   # Windows
  # "$RIG/.venv/bin/python"       -m pip install requests python-dotenv   # *nix
  ```

## Usage

Always invoke with the rig venv's python:

```bash
RIG="$HOME/bonsaiPR_testrig"
PY="$RIG/.venv/Scripts/python.exe"          # Windows  ( .../bin/python on *nix )

$PY harness.py all        # setup -> run 1 -> run 2 (delta) -> verify -> push
$PY harness.py setup      # (re)create the sandbox from the CURRENT scripts
$PY harness.py run 1      # single run of scenario 1 (baseline)
$PY harness.py run 2      # single run of scenario 2 (produces the delta vs run 1)
$PY harness.py verify     # re-verify the last two releases
$PY harness.py push       # commit + push the state snapshots
$PY harness.py clean      # delete sandbox + fixtures (keeps the venv)
```

`all` prints a ✓/✗ summary and the releases URL. Re-run `setup` after editing any
automation script — it copies the current versions into the sandbox.

## Configuration (env vars)

| Var | Default | Meaning |
|-----|---------|---------|
| `TESTBED_OWNER` | `theoryshaw` | GitHub owner of the test repo |
| `TESTBED_REPO`  | `bonsaiPR-testbed` | test repo name |
| `RIG_ROOT`      | `~/bonsaiPR_testrig` | where venv + sandbox + fixtures live |

## Adding / editing scenarios

Scenarios are defined in `scenario(n)` in `harness.py` as three PR lists
(`merged`, `failed`, `skipped`). Change the shas/statuses between scenario 1 and 2
to exercise different delta transitions (a new head sha → *updated*, moving a PR
from `failed` to `merged` → *now merging*, removing one → *dropped*, etc.). The
report is written in the exact format `00_clone_merge_and_create_branch.py`
produces, so the `02_upload` parser consumes it identically to production.

## Notes / limits

- **Scoped by design.** It does not run `main.py`'s clone/merge/build steps or the
  asc/desc/upd retry orchestration — those need the full toolchain and don't
  change the reporting logic. `main.py`'s rescue-event wiring is covered by the
  unit test in the repo.
- Windows: the harness forces UTF-8 on the child processes (`PYTHONIOENCODING`)
  and decodes their output as UTF-8, since the scripts' emoji prints assume the
  UTF-8 Linux host.
- Cleanup: `gh release delete <tag> --cleanup-tag` removes a stray release; or
  delete the whole test repo when done.

#!/usr/bin/env python3
"""
pr_state.py - Normalized per-PR build state, deltas, and an append-only event log.

Why this exists
---------------
The release *body* is human-facing and full of volatile fields (build
timestamp, "first detected", "broken by", merge order). Diffing it directly is
100% noise. This module derives a *stable, sorted* snapshot keyed by PR number
so that:

  * `reports/state.json`  -> committed each run; `git show <c>:...` gives you the
                             snapshot at ANY commit, so an endpoint-delta between
                             any two builds is free.
  * `reports/events.jsonl`-> append-only log of transitions, so "what changed
                             over a range" is a filter on a flat file instead of
                             a history walk.

A PR's *signature* is (status, head_sha). Only those two trigger a transition;
title/author/branch are carried for display but never cause a phantom delta.

IMPORTANT: a delta is only meaningful between snapshots of the SAME merge order
(descending vs descending). `compute_delta` refuses a cross-order diff unless you
pass strict_order=False, because desc-vs-by-updated produces phantom transitions.

CLI
---
    python pr_state.py delta  <commitA> <commitB> [--path REL] [--repo DIR]
    python pr_state.py render <commitA> <commitB> [--path REL] [--repo DIR]
    python pr_state.py series [--since REF]        [--path REL] [--repo DIR]
    python pr_state.py commits                     [--path REL] [--repo DIR]

`commitA`/`commitB` are any git commit-ish (sha, tag, `HEAD~5`, `HEAD@{1.day.ago}`).
"""

import os
import re
import sys
import json
import subprocess
import datetime

SCHEMA_VERSION = 1

# Status buckets. These are the only values that appear in state["prs"][n]["status"].
STATUS_MERGED = "merged"
STATUS_FAILED = "failed"
STATUS_SKIPPED_CONFLICT = "skipped_conflict"
STATUS_SKIPPED_DRAFT = "skipped_draft"

# Default repo-relative location of the committed snapshot.
DEFAULT_REL_PATH = "automation/reports/state.json"
DEFAULT_EVENTS_REL_PATH = "automation/reports/events.jsonl"


# --------------------------------------------------------------------------- #
# Parsing helpers (mirror the shapes generate_release_body() already produces)
# --------------------------------------------------------------------------- #

def _num_title_from_line(pr_line):
    """Pull ('7802', 'Some title') out of a '- **PR #7802**: Some title' line."""
    num_m = re.match(r"- \*\*PR #(\d+)\*\*", pr_line or "")
    num = num_m.group(1) if num_m else None
    title_m = re.match(r"- \*\*PR #\d+\*\*:\s*(.+)", pr_line or "")
    title = title_m.group(1).strip() if title_m else (pr_line or "").strip()
    return num, title


def _head_sha(pr):
    """Return the PR's head commit sha (as reported), or None."""
    lc = pr.get("last_commit")
    if isinstance(lc, dict):
        return (lc.get("sha") or "").strip() or None
    return None


def _sha_eq(a, b):
    """Compare shas tolerant of short/long forms (report mixes 7-char and full)."""
    if not a or not b:
        return a == b
    n = min(len(a), len(b))
    return a[:n].lower() == b[:n].lower()


def _pr_record(pr, status):
    """Build the stable per-PR record stored in state["prs"]."""
    num, title = _num_title_from_line(pr.get("line", ""))
    rec = {
        "status": status,
        "head": _head_sha(pr),
        "title": title,
        "author": pr.get("author"),
        "branch": pr.get("branch"),
        "url": pr.get("url"),
    }
    if status == STATUS_FAILED and pr.get("reason"):
        # Informational only; a reason change alone never triggers a transition.
        rec["reason"] = pr["reason"]
    return num, rec


# --------------------------------------------------------------------------- #
# Build / persist a snapshot
# --------------------------------------------------------------------------- #

def build_state(
    *,
    applied_prs,
    failed_prs,
    skipped_conflict_prs,
    skipped_draft_prs,
    merge_order,
    base=None,
    base_commit=None,
    generated_at=None,
    total_prs=None,
    release_tag=None,
    release_url=None,
):
    """Assemble a normalized, sorted snapshot from the parsed PR lists.

    The four lists are exactly the ones generate_release_body() builds. Keys are
    stringified PR numbers (JSON requires string keys); read them back with
    int(k) when you need numeric sort.

    `release_tag`/`release_url` identify the build this snapshot came from, so a
    later report can link "merges under desc" straight at the desc release that
    actually contains the PR. Both are optional: snapshots written before this
    field existed simply render as plain text.
    """
    prs = {}

    def _ingest(pr_list, status):
        for pr in pr_list or []:
            num, rec = _pr_record(pr, status)
            if num is None:
                continue
            # A PR should appear once; if the report double-lists it, the more
            # "severe" status wins by ingest order (merged ingested last = wins
            # for applied). We ingest failures first so a genuine merge overrides.
            prs[num] = rec

    # Order matters only for the pathological double-listing case above.
    _ingest(failed_prs, STATUS_FAILED)
    _ingest(skipped_conflict_prs, STATUS_SKIPPED_CONFLICT)
    _ingest(skipped_draft_prs, STATUS_SKIPPED_DRAFT)
    _ingest(applied_prs, STATUS_MERGED)

    counts = {
        STATUS_MERGED: sum(1 for r in prs.values() if r["status"] == STATUS_MERGED),
        STATUS_FAILED: sum(1 for r in prs.values() if r["status"] == STATUS_FAILED),
        STATUS_SKIPPED_CONFLICT: sum(
            1 for r in prs.values() if r["status"] == STATUS_SKIPPED_CONFLICT
        ),
        STATUS_SKIPPED_DRAFT: sum(
            1 for r in prs.values() if r["status"] == STATUS_SKIPPED_DRAFT
        ),
        "total": total_prs if total_prs is not None else len(prs),
    }

    if generated_at is None:
        generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    return {
        "schema": SCHEMA_VERSION,
        "generated_at": generated_at,
        "merge_order": (merge_order or "").strip() or "unknown",
        "base": base,
        # The exact commit the PRs were merged onto. A branch name is not enough
        # once profiles can pin a base (RFC-001): "#7798 merged" means different
        # things at different bases, so an aggregate that compares publishers
        # without knowing this is comparing things that are not comparable.
        "base_commit": base_commit,
        "release": {"tag": release_tag, "url": release_url},
        "counts": counts,
        # Sorted numerically now so the committed file is diff-stable.
        "prs": {k: prs[k] for k in sorted(prs, key=int)},
    }


def write_state(state, path):
    """Write a snapshot deterministically (sorted keys, trailing newline)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def load_state(path):
    """Load a snapshot from the working tree, or None if absent/empty."""
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    return json.loads(text) if text else None


# --------------------------------------------------------------------------- #
# Cross-order robustness (asc / desc / upd)
# --------------------------------------------------------------------------- #
#
# main.py builds up to three releases per run, one per merge order. Because a
# conflict between two PRs is resolved by whichever one the order reaches first,
# the merged set differs between orders. Comparing the three snapshots tells you
# which PRs are in a conflict race and which are not.
#
# This is a CHURN signal, not a quality one: a PR that merges under `asc` but not
# `desc` simply lost a race to a PR it textually overlaps with. Nothing about the
# PR itself failed.

# Everything about a merge order lives here, because it used to live in five
# places: this dict plus four separate `if ascending / elif descending / else`
# chains across two scripts. Every one of those chains treated "anything else"
# as by-updated, so adding `recorded` produced a build correctly merged in the
# recorded order and then labelled `[upd]` in its release title, its banner and
# its report.
#
# `recorded` is the order a distilled profile carries (RFC-001 s5.3): the
# sequence its curator actually built in, rather than one of the three guesses.
# It only ever appears for a profile that has an order_seq.
ORDER_META = {
    "ascending": {
        "suffix": "asc",
        "emoji": "⬆️",
        "short": "lowest → highest PR#",
        "label": "ascending — lowest PR# merged first",
    },
    "descending": {
        "suffix": "desc",
        "emoji": "⬇️",
        "short": "highest → lowest PR#",
        "label": "descending — highest PR# merged first",
    },
    "by-updated": {
        "suffix": "upd",
        "emoji": "\U0001f552",
        "short": "most recently updated PR first",
        "label": "by last update — most recently updated PR merged first",
    },
    "recorded": {
        "suffix": "rec",
        "emoji": "\U0001f4cb",
        "short": "the sequence recorded by the curation profile",
        "label": "recorded — the order this profile's curator merged in",
    },
}

ORDER_SUFFIX_BY_NAME = {name: meta["suffix"] for name, meta in ORDER_META.items()}
ORDER_NAME_BY_SUFFIX = {v: k for k, v in ORDER_SUFFIX_BY_NAME.items()}
ORDER_SUFFIXES = tuple(ORDER_SUFFIX_BY_NAME.values())


def order_meta(merge_order):
    """Presentation metadata for a merge order.

    An unrecognised order describes itself rather than being silently reported
    as one of the known ones - mislabelling a build is worse than an ugly label.
    """
    name = (merge_order or "").strip()
    if name in ORDER_META:
        return ORDER_META[name]
    return {
        "suffix": name or "unknown",
        "emoji": "❓",
        "short": f"{name or 'unknown'} order",
        "label": name or "unknown",
    }


def companion_orders(merge_order, names=None):
    """Human-readable list of the other orders, for 'may appear in ...' notes."""
    others = [n for n in (names or ORDER_META) if n != merge_order]
    if not others:
        return "another order"
    if len(others) == 1:
        return others[0]
    return " or ".join([", ".join(others[:-1]), others[-1]])


def order_state_path(reports_dir, suffix):
    """Path to the committed snapshot for one merge order."""
    return os.path.join(reports_dir, f"state.{suffix}.json")


def load_order_states(reports_dir, suffixes=ORDER_SUFFIXES):
    """Load every per-order snapshot; missing or unreadable ones map to None.

    An absent snapshot is normal (first run for that order, a run where the order
    never triggered, or a fresh sandbox), so this never raises.
    """
    states = {}
    for suffix in suffixes:
        try:
            states[suffix] = load_state(order_state_path(reports_dir, suffix))
        except (OSError, ValueError):
            states[suffix] = None
    return states


def robustness_sources(states):
    """[(suffix, generated_at)] for the orders that actually have a snapshot.

    The caller needs this for provenance: the snapshots are written at the END of
    each order's build, so within a run the companion orders' files are still from
    the PREVIOUS run. Any report quoting robustness has to say which vintage it
    compared against.
    """
    return [
        (suffix, (state or {}).get("generated_at"))
        for suffix, state in states.items()
        if state and state.get("prs")
    ]


def order_releases(states):
    """{suffix: {"tag":..., "url":...}} for orders whose snapshot names its build.

    Lets a report turn "merges under desc" into a link to the desc release that
    actually contains the PR. Snapshots written before build_state() recorded the
    release — or by a run that had no tag yet — are simply absent from the map,
    so callers must fall back to plain text.
    """
    releases = {}
    for suffix, state in (states or {}).items():
        release = (state or {}).get("release") or {}
        if release.get("url") or release.get("tag"):
            releases[suffix] = {"tag": release.get("tag"), "url": release.get("url")}
    return releases


def order_link(suffix, releases, label=None):
    """Markdown link to the build that produced `suffix`'s snapshot, else bare text."""
    label = label or suffix
    url = (releases or {}).get(suffix, {}).get("url")
    return f"[{label}]({url})" if url else label


def compute_robustness(states):
    """Per-PR cross-order merge outcome, keyed by stringified PR number.

    `states` is the {suffix: state|None} mapping from load_order_states(). Only
    orders with a usable snapshot participate. Each record is:

        merged_in   [suffix, ...]  orders whose snapshot merged this PR
        blocked_in  [suffix, ...]  orders that saw it but did not merge it
        stable      bool           merged in EVERY order that saw it, having been
                                   seen by at least two

    A PR absent from every snapshot (first seen this run) has no record at all.
    """
    robustness = {}
    for suffix in ORDER_SUFFIXES:
        state = (states or {}).get(suffix)
        if not state or not state.get("prs"):
            continue
        for num, rec in state["prs"].items():
            entry = robustness.setdefault(num, {"merged_in": [], "blocked_in": []})
            bucket = "merged_in" if rec.get("status") == STATUS_MERGED else "blocked_in"
            entry[bucket].append(suffix)

    for entry in robustness.values():
        seen = len(entry["merged_in"]) + len(entry["blocked_in"])
        entry["stable"] = seen >= 2 and not entry["blocked_in"]
    return robustness


# --------------------------------------------------------------------------- #
# Git-backed retrieval (any commit, no checkout)
# --------------------------------------------------------------------------- #

def _git(args, repo_dir=None):
    """Run git and return (returncode, stdout). stderr is swallowed."""
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_dir or None,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


def load_state_at(commit, rel_path=DEFAULT_REL_PATH, repo_dir=None):
    """Snapshot as committed at `commit`, or None if the file didn't exist there."""
    code, out = _git(["show", f"{commit}:{rel_path}"], repo_dir=repo_dir)
    if code != 0 or not out.strip():
        return None
    return json.loads(out)


def state_commits(rel_path=DEFAULT_REL_PATH, repo_dir=None, since=None):
    """Commits that touched the snapshot, OLDEST -> NEWEST.

    `since` is any commit-ish; when given, only commits after it are returned.
    """
    rev = f"{since}..HEAD" if since else "HEAD"
    code, out = _git(
        ["log", "--format=%H", rev, "--", rel_path], repo_dir=repo_dir
    )
    if code != 0:
        return []
    shas = [s for s in out.split() if s]
    shas.reverse()  # git log is newest-first; we want chronological
    return shas


# --------------------------------------------------------------------------- #
# Delta between two snapshots
# --------------------------------------------------------------------------- #

class MergeOrderMismatch(ValueError):
    """Raised when diffing snapshots produced with different merge orders."""


def compute_delta(prev, curr, strict_order=True):
    """Endpoint delta prev -> curr. Works for adjacent OR far-apart snapshots.

    Returns a dict with:
        added          [{pr,status,title,author,url}]      not in prev
        removed        [{pr,last_status,title}]            gone from curr
        status_changed [{pr,from,to,title,author,url}]     bucket transition
        updated        [{pr,status,from_head,to_head,...}] same status, new head
    plus prev/curr generated_at and merge_order for context.

    NOTE: this is a *net* endpoint delta. If a PR failed and recovered between
    prev and curr, it shows as unchanged here — use series_events() for the
    intermediate transitions.
    """
    prev = prev or {"prs": {}, "merge_order": None, "generated_at": None}
    curr = curr or {"prs": {}, "merge_order": None, "generated_at": None}

    po, co = prev.get("merge_order"), curr.get("merge_order")
    if strict_order and po and co and po != co:
        raise MergeOrderMismatch(
            f"Refusing to diff merge orders {po!r} vs {co!r}; "
            f"pass strict_order=False to override."
        )

    p, c = prev.get("prs", {}), curr.get("prs", {})
    added, removed, status_changed, updated = [], [], [], []

    for num in sorted(set(p) | set(c), key=int):
        pr_prev, pr_curr = p.get(num), c.get(num)
        n = int(num)

        if pr_curr and not pr_prev:
            added.append(
                {
                    "pr": n,
                    "status": pr_curr["status"],
                    "title": pr_curr.get("title"),
                    "author": pr_curr.get("author"),
                    "url": pr_curr.get("url"),
                }
            )
        elif pr_prev and not pr_curr:
            removed.append(
                {"pr": n, "last_status": pr_prev["status"], "title": pr_prev.get("title")}
            )
        else:  # in both
            if pr_prev["status"] != pr_curr["status"]:
                status_changed.append(
                    {
                        "pr": n,
                        "from": pr_prev["status"],
                        "to": pr_curr["status"],
                        "title": pr_curr.get("title"),
                        "author": pr_curr.get("author"),
                        "url": pr_curr.get("url"),
                    }
                )
            elif not _sha_eq(pr_prev.get("head"), pr_curr.get("head")):
                updated.append(
                    {
                        "pr": n,
                        "status": pr_curr["status"],
                        "from_head": pr_prev.get("head"),
                        "to_head": pr_curr.get("head"),
                        "title": pr_curr.get("title"),
                        "url": pr_curr.get("url"),
                    }
                )

    return {
        "prev_generated_at": prev.get("generated_at"),
        "curr_generated_at": curr.get("generated_at"),
        "merge_order": co or po,
        "added": added,
        "removed": removed,
        "status_changed": status_changed,
        "updated": updated,
    }


def delta_is_empty(delta):
    return not (
        delta["added"] or delta["removed"] or delta["status_changed"] or delta["updated"]
    )


# --------------------------------------------------------------------------- #
# Event log (append-only)
# --------------------------------------------------------------------------- #

def delta_to_events(delta, ts=None):
    """Flatten a delta into one JSONL row per change, for events.jsonl."""
    ts = ts or delta.get("curr_generated_at") or datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    order = delta.get("merge_order")
    rows = []
    for a in delta["added"]:
        rows.append({"ts": ts, "order": order, "pr": a["pr"],
                     "event": "added", "to": a["status"]})
    for r in delta["removed"]:
        rows.append({"ts": ts, "order": order, "pr": r["pr"],
                     "event": "removed", "from": r["last_status"]})
    for s in delta["status_changed"]:
        rows.append({"ts": ts, "order": order, "pr": s["pr"],
                     "event": "status", "from": s["from"], "to": s["to"]})
    for u in delta["updated"]:
        rows.append({"ts": ts, "order": order, "pr": u["pr"], "event": "updated",
                     "status": u["status"], "from_head": u["from_head"],
                     "to_head": u["to_head"]})
    rows.sort(key=lambda r: r["pr"])
    return rows


def append_events(events_path, events):
    """Append event rows to a JSONL file (creates it if needed)."""
    if not events:
        return
    os.makedirs(os.path.dirname(os.path.abspath(events_path)), exist_ok=True)
    with open(events_path, "a", encoding="utf-8") as f:
        for row in events:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rescue_events(rescued_prs, *, rescued_by_order, baseline_order="asc", ts=None):
    """Events for PRs an alternate merge order merged that the baseline could not.

    The baseline (ascending) build conflict-skipped these PRs; a later order
    (descending / by-updated) then merged them. This is a *within-run,
    cross-order* fact — not a run-to-run transition — so it lives only in the
    alternate order's event log and is never produced by series_events(), which
    only sees single-order snapshots.

    `rescued_prs` is any iterable of PR numbers (ints or numeric strings).
    """
    if ts is None:
        ts = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    rows = []
    for pr in sorted(int(p) for p in rescued_prs):
        rows.append(
            {
                "ts": ts,
                "order": rescued_by_order,
                "pr": pr,
                "event": "rescued",
                "from_order": baseline_order,
            }
        )
    return rows


def series_events(rel_path=DEFAULT_REL_PATH, repo_dir=None, since=None,
                  strict_order=False):
    """Reconstruct the full transition history by walking adjacent commits.

    This is the "series of deltas" answer: it visits every commit that touched
    the snapshot and yields the events between each adjacent pair. Use it to
    catch PRs that flapped (failed then recovered) between two far-apart points,
    which an endpoint delta hides. Independent of events.jsonl, so it also works
    retroactively over history that predates the log.
    """
    shas = state_commits(rel_path=rel_path, repo_dir=repo_dir, since=since)
    all_events = []
    prev_state = None
    for sha in shas:
        curr_state = load_state_at(sha, rel_path=rel_path, repo_dir=repo_dir)
        if curr_state is None:
            continue
        if prev_state is not None:
            try:
                delta = compute_delta(prev_state, curr_state,
                                      strict_order=strict_order)
            except MergeOrderMismatch:
                prev_state = curr_state
                continue
            for row in delta_to_events(delta):
                row["commit"] = sha
                all_events.append(row)
        prev_state = curr_state
    return all_events


# --------------------------------------------------------------------------- #
# Human-facing summary for the release page
# --------------------------------------------------------------------------- #

def _pr_link(pr, url):
    return f"[#{pr}]({url})" if url else f"#{pr}"


def render_delta_md(delta, curr=None, heading="### 🔁 Changes since last build"):
    """Short markdown block for the release body — the delta, not the full state."""
    if delta_is_empty(delta):
        body = "_No PR-level changes since the previous build._"
    else:
        # Friendly groupings derived from the raw transitions.
        newly_merged = [s for s in delta["status_changed"] if s["to"] == STATUS_MERGED]
        newly_broken = [s for s in delta["status_changed"]
                        if s["from"] == STATUS_MERGED and s["to"] == STATUS_FAILED]
        other_changed = [s for s in delta["status_changed"]
                         if s not in newly_merged and s not in newly_broken]

        def _bullets(items, fmt):
            return "\n".join(fmt(i) for i in items)

        parts = []
        if delta["added"]:
            parts.append(
                f"**New PRs ({len(delta['added'])})**\n"
                + _bullets(delta["added"],
                           lambda a: f"- {_pr_link(a['pr'], a.get('url'))} "
                                     f"→ {a['status']} — {a.get('title') or ''}")
            )
        if newly_merged:
            parts.append(
                f"**Now merging ({len(newly_merged)})**\n"
                + _bullets(newly_merged,
                           lambda s: f"- {_pr_link(s['pr'], s.get('url'))} "
                                     f"({s['from']} → merged) — {s.get('title') or ''}")
            )
        if newly_broken:
            parts.append(
                f"**Newly failing ({len(newly_broken)})**\n"
                + _bullets(newly_broken,
                           lambda s: f"- {_pr_link(s['pr'], s.get('url'))} "
                                     f"(merged → failed) — {s.get('title') or ''}")
            )
        if other_changed:
            parts.append(
                f"**Status changed ({len(other_changed)})**\n"
                + _bullets(other_changed,
                           lambda s: f"- {_pr_link(s['pr'], s.get('url'))} "
                                     f"({s['from']} → {s['to']}) — {s.get('title') or ''}")
            )
        if delta["updated"]:
            parts.append(
                f"**Updated (new commits) ({len(delta['updated'])})**\n"
                + _bullets(delta["updated"],
                           lambda u: f"- {_pr_link(u['pr'], u.get('url'))} "
                                     f"— {u.get('title') or ''}")
            )
        if delta["removed"]:
            parts.append(
                f"**Dropped ({len(delta['removed'])})** "
                f"_(merged upstream or PR closed)_\n"
                + _bullets(delta["removed"],
                           lambda r: f"- #{r['pr']} (was {r['last_status']}) "
                                     f"— {r.get('title') or ''}")
            )
        body = "\n\n".join(parts)

    order = delta.get("merge_order")
    order_note = f" _(merge order: {order})_" if order else ""
    return f"{heading}{order_note}\n\n{body}\n"


# --------------------------------------------------------------------------- #
# CLI — test it against your real git history immediately
# --------------------------------------------------------------------------- #

def _parse_common(argv):
    rel_path, repo_dir, since = DEFAULT_REL_PATH, None, None
    rest = []
    it = iter(argv)
    for a in it:
        if a == "--path":
            rel_path = next(it)
        elif a == "--repo":
            repo_dir = next(it)
        elif a == "--since":
            since = next(it)
        else:
            rest.append(a)
    return rel_path, repo_dir, since, rest


def main(argv):
    # The cron host is UTF-8, but a Windows console defaults to cp1252 and would
    # choke on emoji in rendered output. Force UTF-8 stdout where supported.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    rel_path, repo_dir, since, rest = _parse_common(args)

    if cmd in ("delta", "render"):
        if len(rest) != 2:
            print(f"usage: pr_state.py {cmd} <commitA> <commitB>", file=sys.stderr)
            return 2
        a, b = rest
        sa = load_state_at(a, rel_path=rel_path, repo_dir=repo_dir)
        sb = load_state_at(b, rel_path=rel_path, repo_dir=repo_dir)
        if sa is None or sb is None:
            print("❌ Could not load one of the snapshots from git.", file=sys.stderr)
            return 1
        delta = compute_delta(sa, sb, strict_order=False)
        if cmd == "delta":
            print(json.dumps(delta, indent=2, ensure_ascii=False))
        else:
            print(render_delta_md(delta, sb))
        return 0

    if cmd == "series":
        events = series_events(rel_path=rel_path, repo_dir=repo_dir, since=since)
        for row in events:
            print(json.dumps(row, ensure_ascii=False))
        return 0

    if cmd == "commits":
        for sha in state_commits(rel_path=rel_path, repo_dir=repo_dir, since=since):
            print(sha)
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

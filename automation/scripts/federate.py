#!/usr/bin/env python3
"""
federate.py - Aggregate curated-build manifests into per-PR signals.

Why this exists
---------------
RFC-001 (proposals/RFC-001-federated-curated-builds.md) proposes that people
publish their own *curated* BonsaiPR builds, and that those curations aggregate
into evidence a maintainer can act on. This is phase 0 of that: the aggregation
math and its rendering, run against data the repo already produces, so the idea
can be judged on real output before anyone is asked to change the pipeline.

The key observation from RFC-001 s3.1 is that `pr_state.compute_robustness()` is
already an aggregator - it takes N independent builds of the same PR set and,
per PR, reports which merged it and which did not. It just happens that today
N=3 and the sources are one publisher's own asc/desc/upd merge orders. This
module generalizes the source key from "merge order" to an arbitrary
(publisher, profile, order) triple, so phase 2 becomes a change of *loader*
rather than a change of *math*.

Phase 0 sources are the local `state.<order>.json` files. Because those three
builds all come from one publisher running one (implicit) profile, treating them
as three publishers is a deliberate fiction - see SYNTHETIC below.

What this can and cannot say
----------------------------
Signals are only emitted where the underlying data actually supports them.
RFC-001 s8.1 is emphatic that an over-read signal is worse than no signal, so
anything not derivable is reported as unavailable rather than approximated:

  available now   merged_by, blocked_by, stable, divergence, streak, churn
  needs phase 1   selected_by, excluded_by, objections  (no profiles exist yet)
  needs new data  rivals - the reports record *that* a PR conflicts with other
                  PRs and which orders it merges under, but not *which* PR won
                  the race, so the pairing cannot be reconstructed. Recording
                  the winning PR number at conflict time is a small change to
                  00_clone_merge_and_create_branch.py and would unlock it.

CLI
---
    python federate.py aggregate [--reports DIR] [--repo DIR] [--out DIR]
    python federate.py digest    [--reports DIR] [--repo DIR] [--top N]

`aggregate` writes federation.json + DIGEST.md; `digest` prints the summary to
stdout without writing anything.
"""

import os
import re
import sys
import json
import argparse
import datetime
import subprocess
from collections import defaultdict

import pr_state

SCHEMA_VERSION = 1

# Phase 0 has one real publisher (whoever's checkout this is) running three
# merge orders. Aggregating "distinct publishers" over that yields 1, which
# tells you nothing - so phase 0 promotes each merge order to a synthetic
# publisher. This is a fiction and every rendered artifact says so out loud,
# because the whole point of RFC-001 s9 is that publisher count is the unit
# that must not be inflated.
LOCAL_PUBLISHER = "local"

# Streak and churn are single-lineage measures (see aggregate()). `asc` is the
# canonical diff lineage for this pipeline, so it is the one they are quoted
# against; if it is missing, the first available order is used instead.
CANONICAL_ORDER = "asc"

DEFAULT_REPORTS_REL = os.path.join("automation", "reports")


# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #

class Source:
    """One build's manifest, plus who produced it.

    In phase 0 `publisher` is the merge-order suffix (the fiction described
    above). In phase 2 it becomes the manifest's `publisher.id`, and nothing
    downstream of here has to change.
    """

    def __init__(self, sid, publisher, profile, order, state):
        self.id = sid
        self.publisher = publisher
        self.profile = profile
        self.order = order
        self.state = state or {}

    @property
    def prs(self):
        return self.state.get("prs", {})

    @property
    def generated_at(self):
        return self.state.get("generated_at")

    def __repr__(self):
        return f"<Source {self.id} publisher={self.publisher} prs={len(self.prs)}>"


def load_local_sources(reports_dir, synthetic=True):
    """Phase 0 loader: the three per-order snapshots in `reports_dir`.

    Orders with no snapshot yet are skipped silently - that is normal on a fresh
    checkout or for an order that has never triggered.
    """
    sources = []
    states = pr_state.load_order_states(reports_dir)
    for suffix in pr_state.ORDER_SUFFIXES:
        state = states.get(suffix)
        if not state or not state.get("prs"):
            continue
        sources.append(
            Source(
                sid=suffix,
                publisher=suffix if synthetic else LOCAL_PUBLISHER,
                profile="everything",
                order=pr_state.ORDER_NAME_BY_SUFFIX.get(suffix, suffix),
                state=state,
            )
        )
    return sources


# --------------------------------------------------------------------------- #
# Build timeline (for streaks)
# --------------------------------------------------------------------------- #

def _git(args, repo_dir=None):
    result = subprocess.run(
        ["git"] + args, cwd=repo_dir or None, capture_output=True, text=True
    )
    return result.returncode, result.stdout


def build_times(order_suffix, repo_dir=None, reports_rel=DEFAULT_REPORTS_REL):
    """Commit timestamps of every build that wrote this order's snapshot.

    Returned NEWEST -> OLDEST as ISO-8601 UTC strings. One `git log` call rather
    than one `git show` per commit: the snapshots themselves are not needed, only
    when they landed, which is all a streak count requires.
    """
    rel = f"{reports_rel}/state.{order_suffix}.json".replace("\\", "/")
    code, out = _git(["log", "--format=%cI", "--", rel], repo_dir=repo_dir)
    if code != 0:
        return []
    stamps = []
    for line in out.split():
        line = line.strip()
        if not line:
            continue
        stamps.append(_to_utc(line))
    return stamps


def _to_utc(ts):
    """Normalize any ISO-8601 stamp (with or without offset) to `...Z` UTC."""
    if not ts:
        return None
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return ts
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Events -> per-PR history
# --------------------------------------------------------------------------- #

def load_events(reports_dir, order_suffix):
    """Read one order's append-only event log. Missing/corrupt lines are skipped."""
    path = os.path.join(reports_dir, f"events.{order_suffix}.jsonl")
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def merged_since(events_for_pr):
    """Timestamp at which this PR most recently *became* merged, or None.

    Replays one order's event log in order. None means the log never records a
    transition into merged, which - for a PR the snapshot says is merged now -
    means it was already merged before the log began.

    This must be computed against a SINGLE order's events. Each order is an
    independent lineage (a PR can be merged in `asc` and conflict-skipped in
    `desc` on the same run), so interleaving two logs produces a status history
    that never actually happened.
    """
    state, since = None, None
    for e in events_for_pr:
        ev, ts = e.get("event"), _to_utc(e.get("ts"))
        if ev == "updated":
            continue  # new head commit, same bucket - not a transition
        if ev == "removed":
            new = None
        elif ev in ("added", "status"):
            new = e.get("to")
        else:
            continue
        if new == pr_state.STATUS_MERGED:
            if state != pr_state.STATUS_MERGED:
                since = ts
        else:
            since = None
        state = new
    return since


def streak_for(events_for_pr, stamps, currently_merged, now=None):
    """How long this PR has been continuously merged, in builds and days.

    `bounded=True` means the log records no transition into merged, so the PR was
    already merged when the log began and the true streak is at least this long.
    Saying so matters: treating it as exact would silently understate every
    long-lived PR by however old the log is.
    """
    if not currently_merged:
        return None
    since = merged_since(events_for_pr)
    bounded = since is None
    if bounded:
        since = stamps[-1] if stamps else None  # oldest recorded build
    if not since:
        return None

    builds = sum(1 for s in stamps if s and s >= since)
    start = _parse(since)
    end = _parse(now) or datetime.datetime.now(datetime.timezone.utc)
    days = round((end - start).total_seconds() / 86400.0, 1) if start else None
    return {"builds": builds, "days": days, "since": since, "bounded": bounded}


def churn_for(events_for_pr):
    """How often this PR has flipped between buckets in one order's lineage.

    High churn is a *conflict-race* signal, not a quality one (see pr_state's
    note on cross-order robustness): a PR that keeps winning and losing races to
    a textual neighbour will flap without anything being wrong with it.
    """
    rows = [e for e in events_for_pr if e.get("event") == "status"]
    if not rows:
        return {"transitions": 0, "last": None}
    last = max((_to_utc(e.get("ts")) for e in rows if e.get("ts")), default=None)
    return {"transitions": len(rows), "last": last}


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #

def aggregate(sources, events_by_order=None, stamps_by_order=None, now=None):
    """Per-PR signals across N sources, keyed by stringified PR number.

    This is `pr_state.compute_robustness()` generalized: instead of bucketing by
    merge-order suffix it buckets by *publisher*, so two builds from the same
    publisher count once. RFC-001 s9 makes that the load-bearing anti-gaming
    rule - anyone can run fifty instances, nobody can be fifty people.
    """
    events_by_order = events_by_order or {}
    stamps_by_order = stamps_by_order or {}

    # Streak and churn are computed against ONE lineage, not all three pooled.
    # Each order is independent: a PR can be merged in `asc` and conflict-skipped
    # in `desc` on the same run, so interleaving the logs invents a history that
    # never happened, and pooling the build timestamps triple-counts every run.
    # `asc` is the canonical lineage elsewhere in this pipeline, so it is the one
    # quoted here; the per-source statuses below still cover all three.
    lineage = CANONICAL_ORDER if CANONICAL_ORDER in events_by_order else (
        sorted(events_by_order)[0] if events_by_order else None
    )
    lineage_events = defaultdict(list)
    for e in events_by_order.get(lineage, []):
        lineage_events[str(e.get("pr"))].append(e)
    for rows in lineage_events.values():
        rows.sort(key=lambda e: e.get("ts") or "")
    lineage_stamps = sorted(
        (s for s in stamps_by_order.get(lineage, []) if s), reverse=True
    )

    signals = {}
    for src in sources:
        for num, rec in src.prs.items():
            entry = signals.setdefault(
                num,
                {
                    "merged_by": set(),
                    "blocked_by": set(),
                    "status_by_source": {},
                    "title": rec.get("title"),
                    "author": rec.get("author"),
                    "url": rec.get("url"),
                },
            )
            entry["status_by_source"][src.id] = rec.get("status")
            bucket = "merged_by" if rec.get("status") == pr_state.STATUS_MERGED else "blocked_by"
            entry[bucket].add(src.publisher)
            # Display fields come from whichever source saw it last; they are
            # informational and never participate in a comparison.
            for k in ("title", "author", "url"):
                if rec.get(k):
                    entry[k] = rec[k]

    out = {}
    for num in sorted(signals, key=int):
        e = signals[num]
        merged = sorted(e["merged_by"])
        blocked = sorted(e["blocked_by"])
        seen = len(set(merged) | set(blocked))
        pr_events = lineage_events.get(num, [])
        rec = {
            "merged_by": merged,
            "blocked_by": blocked,
            "publishers_seen": seen,
            "stable": seen >= 2 and not blocked,
            "divergence": bool(merged and blocked),
            "status_by_source": e["status_by_source"],
            "lineage": lineage,
            "churn": churn_for(pr_events),
            "title": e["title"],
            "author": e["author"],
            "url": e["url"],
        }
        rec["streak"] = streak_for(
            pr_events,
            lineage_stamps,
            currently_merged=e["status_by_source"].get(lineage) == pr_state.STATUS_MERGED,
            now=now,
        )
        out[num] = rec
    return out


def unavailable_signals():
    """Signals RFC-001 defines that phase 0 genuinely cannot compute.

    Emitted into federation.json so a consumer can tell "zero" from "unknown" -
    the distinction the whole s8.1 table exists to protect.
    """
    return {
        "selected_by": "requires profiles (RFC-001 phase 1) - every build here selects everything",
        "excluded_by": "requires profiles (RFC-001 phase 1)",
        "objections": "requires profiles (RFC-001 phase 1)",
        "lost_to": "requires profiles (RFC-001 phase 1)",
        "rivals": "requires recording the winning PR number at conflict time; "
                  "the reports currently record that a conflict happened and which "
                  "orders a PR merges under, but not which PR it lost to",
        "verification": "requires curator-published smoke results (RFC-001 phase 5)",
    }


def build_federation(sources, signals, synthetic=True, now=None):
    """The full machine-readable artifact."""
    return {
        "schema": SCHEMA_VERSION,
        "generated_at": now
        or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": 0,
        "synthetic_publishers": bool(synthetic),
        "sources": [
            {
                "id": s.id,
                "publisher": s.publisher,
                "profile": s.profile,
                "order": s.order,
                "generated_at": s.generated_at,
                "prs": len(s.prs),
            }
            for s in sources
        ],
        "publishers": sorted({s.publisher for s in sources}),
        "unavailable": unavailable_signals(),
        "prs": signals,
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def _pr_link(num, url):
    return f"[#{num}]({url})" if url else f"#{num}"


def _short(text, n=58):
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def render_digest(fed, top=15):
    """Maintainer-facing summary. Every claim names its provenance."""
    signals = fed["prs"]
    sources = fed["sources"]
    n_pub = len(fed["publishers"])

    lines = []
    lines.append("# BonsaiPR federation digest")
    lines.append("")
    lines.append(f"Generated: {fed['generated_at']}  ·  RFC-001 phase {fed['phase']}")
    lines.append("")

    if fed.get("synthetic_publishers"):
        lines.append(
            "> ⚠️ **Synthetic publishers.** This run has one real publisher. Each merge "
            "order is being counted as a separate publisher so the aggregation has "
            "something to compare — the numbers below exercise the math, they do not "
            "demonstrate independent agreement. Real federation begins at phase 2."
        )
        lines.append("")

    lines.append("## Sources")
    lines.append("")
    lines.append("| source | publisher | profile | order | PRs | snapshot |")
    lines.append("|---|---|---|---|---:|---|")
    for s in sources:
        lines.append(
            f"| `{s['id']}` | {s['publisher']} | {s['profile']} | {s['order']} "
            f"| {s['prs']} | {s['generated_at'] or '—'} |"
        )
    lines.append("")

    total = len(signals)
    stable = [n for n, r in signals.items() if r["stable"]]
    diverged = [n for n, r in signals.items() if r["divergence"]]
    merged_all = [n for n, r in signals.items() if r["merged_by"] and not r["blocked_by"]]
    never = [n for n, r in signals.items() if not r["merged_by"]]

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- PRs seen by at least one source: **{total}**")
    lines.append(f"- Merged by every publisher that saw them: **{len(merged_all)}**")
    lines.append(f"- Stable (merged everywhere, seen by ≥2 publishers): **{len(stable)}**")
    lines.append(f"- **Divergent** (merged for some, blocked for others): **{len(diverged)}**")
    lines.append(f"- Merged by nobody: **{len(never)}**")
    lines.append("")
    lines.append(
        "Divergence is the interesting bucket: those PRs are sensitive to merge order "
        "or base, which is a fact about the *ecosystem* rather than about the PR. "
        "Under real federation the same computation reads as \"some curators can "
        "carry this and others cannot.\""
    )
    lines.append("")

    # --- divergent, ranked by how split they are ---
    if diverged:
        lines.append(f"## Divergent PRs ({len(diverged)})")
        lines.append("")
        lines.append("| PR | merged by | blocked by | title |")
        lines.append("|---|---|---|---|")
        ranked = sorted(
            diverged,
            key=lambda n: (-len(signals[n]["blocked_by"]), -len(signals[n]["merged_by"]), int(n)),
        )
        for n in ranked[:top]:
            r = signals[n]
            lines.append(
                f"| {_pr_link(n, r['url'])} | {', '.join(r['merged_by'])} "
                f"| {', '.join(r['blocked_by'])} | {_short(r['title'])} |"
            )
        if len(ranked) > top:
            lines.append(f"| … | | | _{len(ranked) - top} more_ |")
        lines.append("")

    # --- longest-standing merges ---
    with_streak = [
        (n, r) for n, r in signals.items() if r.get("streak") and r["streak"].get("days") is not None
    ]
    if with_streak:
        lines.append(f"## Longest continuously-merged (top {top})")
        lines.append("")
        lines.append("| PR | builds | days | title |")
        lines.append("|---|---:|---:|---|")
        for n, r in sorted(
            with_streak, key=lambda kv: (-(kv[1]["streak"]["days"] or 0), int(kv[0]))
        )[:top]:
            st = r["streak"]
            mark = "≥" if st["bounded"] else ""
            lines.append(
                f"| {_pr_link(n, r['url'])} | {mark}{st['builds']} | {mark}{st['days']} "
                f"| {_short(r['title'])} |"
            )
        lines.append("")
        lines.append(
            "_`≥` means the PR was already merged when the event log began, so the true "
            "streak is at least this long._"
        )
        lines.append("")

    # --- churn ---
    churny = [(n, r) for n, r in signals.items() if r["churn"]["transitions"] > 0]
    if churny:
        lines.append(f"## Most churn (top {top})")
        lines.append("")
        lines.append("| PR | transitions | last | title |")
        lines.append("|---|---:|---|---|")
        for n, r in sorted(
            churny, key=lambda kv: (-kv[1]["churn"]["transitions"], int(kv[0]))
        )[:top]:
            c = r["churn"]
            lines.append(
                f"| {_pr_link(n, r['url'])} | {c['transitions']} | {c['last'] or '—'} "
                f"| {_short(r['title'])} |"
            )
        lines.append("")
        lines.append(
            "_Churn is a conflict-race signal, not a quality one — a PR that repeatedly "
            "wins and loses a race against a textual neighbour will flap without anything "
            "being wrong with it._"
        )
        lines.append("")

    lines.append("## Not computed")
    lines.append("")
    lines.append(
        "RFC-001 §8.1 treats an over-read signal as worse than no signal, so these are "
        "reported as unavailable rather than approximated:"
    )
    lines.append("")
    for k, why in sorted(fed["unavailable"].items()):
        lines.append(f"- **`{k}`** — {why}")
    lines.append("")

    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _repo_root(start=None):
    """Locate the repo root from this file, so the script works from anywhere."""
    here = start or os.path.dirname(os.path.abspath(__file__))
    code, out = _git(["rev-parse", "--show-toplevel"], repo_dir=here)
    if code == 0 and out.strip():
        return out.strip()
    return os.path.abspath(os.path.join(here, "..", ".."))


def _collect(reports_dir, repo_dir, synthetic):
    sources = load_local_sources(reports_dir, synthetic=synthetic)
    if not sources:
        return None, None, None
    events_by_order, stamps_by_order = {}, {}
    for s in sources:
        events_by_order[s.id] = load_events(reports_dir, s.id)
        stamps_by_order[s.id] = build_times(s.id, repo_dir=repo_dir)
    return sources, events_by_order, stamps_by_order


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    root = _repo_root()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("command", choices=["aggregate", "digest"])
    ap.add_argument("--reports", default=os.path.join(root, DEFAULT_REPORTS_REL))
    ap.add_argument("--repo", default=root)
    ap.add_argument("--out", default=os.path.join(root, "federation"))
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument(
        "--real-publishers",
        action="store_true",
        help="do NOT promote merge orders to publishers (phase 0 output becomes trivial)",
    )
    args = ap.parse_args(argv)

    synthetic = not args.real_publishers
    sources, events, stamps = _collect(args.reports, args.repo, synthetic)
    if not sources:
        print(f"❌ No state.<order>.json snapshots under {args.reports}", file=sys.stderr)
        return 1

    signals = aggregate(sources, events, stamps)
    fed = build_federation(sources, signals, synthetic=synthetic)
    digest = render_digest(fed, top=args.top)

    if args.command == "digest":
        print(digest)
        return 0

    os.makedirs(args.out, exist_ok=True)
    fed_path = os.path.join(args.out, "federation.json")
    dig_path = os.path.join(args.out, "DIGEST.md")
    with open(fed_path, "w", encoding="utf-8") as f:
        json.dump(fed, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    with open(dig_path, "w", encoding="utf-8") as f:
        f.write(digest)

    print(f"✅ {len(signals)} PRs across {len(fed['publishers'])} publisher(s)")
    print(f"   {fed_path}")
    print(f"   {dig_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
base_advisor.py - Which base commit lets the most of a curation land?

Why this exists
---------------
Upstream drift, not PR quality, is what breaks most merges. A PR that applied
cleanly when it was written conflicts months later because the base moved under
it. A curated build can therefore pin its base (profile `base.commit`) and keep
building without asking every contributor to rebase - at the cost of not
receiving upstream fixes until the pin advances.

That trade is only worth making with numbers, and the numbers change every day
as upstream moves. There are two different questions here, and mixing them up
has already produced one wrong recommendation:

    default    at THIS base, how many of my selected PRs merge onto the base
               ON THEIR OWN?
    --in-stack at THIS base, how many land when merged IN ORDER, each onto the
               result of the last - which is what the build does?

The default is fast and answers the narrower question. It cannot see a PR that
merges onto the base perfectly but collides with another PR merged before it -
and that is not a corner case: on the reference profile 158/160 PRs merge in
isolation while nine still need a pinned fallback in the real build. So a `+0`
in the default mode's "gained" column means "this mode cannot tell", not "no
benefit". Use `--in-stack` before deciding to move a base.

Neither mode rebases, checks out, or writes a ref: `merge-tree --write-tree`
merges into the object store, and `--in-stack` chains the results with
`commit-tree`, so an entire build replays with no working tree.

Reading the output
------------------
The interesting column is not the total, it is what moving the pin would cost.
"Advance the base" is cheap when a newer candidate loses nothing, and expensive
when it drops PRs the curation exists to carry. Contributors rebasing is what
makes a newer base cheap again - so a persistent loss column is a list of PRs
worth nudging, not a reason to stay pinned forever. In `--in-stack` mode the
column that matters is PRs moving from `pinned` to `head`: those are the ones an
advance actually frees.

CLI
---
    python base_advisor.py --profile NAME --repo DIR [--candidates N]
    python base_advisor.py --profile NAME --repo DIR --at <commit> [--at <commit>]
    python base_advisor.py --profile NAME --repo DIR --in-stack
"""

import os
import sys
import json
import argparse
import subprocess

import bonsaipr_profile

UPSTREAM_DEFAULT = "https://github.com/IfcOpenShell/IfcOpenShell.git"


def git(args, repo, check=False):
    r = subprocess.run(
        ["git"] + args, cwd=repo, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def fetch_pr_heads(repo, numbers, remote="origin", batch=25, quiet=False):
    """Fetch each PR head into refs/baseadv/<n>. Returns the refs that landed."""
    got = []
    for i in range(0, len(numbers), batch):
        chunk = numbers[i : i + batch]
        specs = [f"+refs/pull/{n}/head:refs/baseadv/{n}" for n in chunk]
        r = subprocess.run(
            ["git", "fetch", "-q", remote] + specs,
            cwd=repo, capture_output=True, text=True,
        )
        if r.returncode != 0 and not quiet:
            print(f"  ⚠️  fetch batch failed: {r.stderr.strip()[:120]}")
        for n in chunk:
            if git(["rev-parse", "--verify", "-q", f"refs/baseadv/{n}"], repo).strip():
                got.append(n)
    return got


def cleanup_refs(repo):
    """Remove the temporary refs. Always call this; they are not the user's."""
    listing = git(["for-each-ref", "--format=delete %(refname)", "refs/baseadv/"], repo)
    if listing.strip():
        subprocess.run(
            ["git", "update-ref", "--stdin"], cwd=repo,
            input=listing, capture_output=True, text=True,
        )


def merges_clean(repo, base, ref):
    r = subprocess.run(
        ["git", "merge-tree", "--write-tree", base, ref],
        cwd=repo, capture_output=True, text=True,
    )
    return r.returncode == 0


def merge_into(repo, head, ref, message):
    """Merge `ref` into commit `head`, returning the new commit, or None.

    `merge-tree --write-tree` writes the merged tree into the object store, and
    `commit-tree` wraps it into a real merge commit — so a whole build can be
    replayed with no worktree, no checkout and no refs.
    """
    r = subprocess.run(
        ["git", "merge-tree", "--write-tree", head, ref],
        cwd=repo, capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    tree = r.stdout.split("\n", 1)[0].strip()
    if not tree:
        return None
    parent = git(["rev-parse", ref], repo).strip()
    out = git(
        ["commit-tree", tree, "-p", head, "-p", parent, "-m", message],
        repo, check=True,
    ).strip()
    return out or None


def evaluate_in_stack(repo, bases, refs, order, pins):
    """Replay the curation at each base, accumulating as the pipeline does.

    `merges_clean` asks whether a PR merges onto the *base* by itself. That is a
    different question from the one the build answers, and the gap is not
    academic: on the reference profile 158/160 PRs merge onto the base in
    isolation, while nine of them still need a pinned fallback because they
    collide with PRs merged before them. An in-isolation score cannot see a
    stack interaction at all, so its "gained" column reads +0 whether or not
    advancing the base would actually help.

    This mirrors stage 0 instead: merge in order, try each PR's head first, fall
    back to its pinned commit, and skip it if neither applies.
    """
    # fetch_pr_heads yields ref names as strings; the order and pins are ints.
    available = {str(x) for x in refs}
    result = {}
    for label, sha in bases:
        head = sha
        landed, pinned_use, dropped = set(), set(), set()
        for n in order:
            if str(n) not in available:
                continue
            nxt = merge_into(repo, head, f"refs/baseadv/{n}", f"pr {n}")
            if nxt:
                head = nxt
                landed.add(n)
                continue
            pin = pins.get(int(n))
            nxt = merge_into(repo, head, pin, f"pr {n} (pinned)") if pin else None
            if nxt:
                head = nxt
                pinned_use.add(n)
            else:
                dropped.add(n)
        result[sha] = {
            "landed": landed, "pinned": pinned_use, "dropped": dropped,
        }
        print(
            f"  {label:>8} {sha[:10]}  {len(landed):>4} at head, "
            f"{len(pinned_use)} pinned, {len(dropped)} dropped"
        )
    return result


def render_in_stack(bases, results, refs, repo):
    lines = ["", "=" * 68, "Base advisor — in-stack replay", "=" * 68, ""]
    lines.append("  Merged in curation order, each PR onto the result of the last —")
    lines.append("  the same question the build asks. 'pinned' PRs merge only at an")
    lines.append("  earlier validated commit; 'dropped' merge at neither.")
    lines.append("")
    for label, sha in bases:
        r = results[sha]
        when = git(["log", "-1", "--format=%ci", sha], repo).strip()[:16]
        lines.append(
            f"  {label:>8}  {sha[:10]}  {when}   "
            f"{len(r['landed']):>3} head  {len(r['pinned']):>2} pinned  "
            f"{len(r['dropped']):>2} dropped"
        )
    lines.append("")

    first = bases[0][1]
    if len(bases) > 1:
        base_r = results[first]
        lines.append(f"  Relative to {bases[0][0]} ({first[:10]}):")
        for label, sha in bases[1:]:
            r = results[sha]
            freed = sorted(base_r["pinned"] & r["landed"], key=int)
            newly_pinned = sorted(base_r["landed"] & r["pinned"], key=int)
            newly_dropped = sorted(
                (base_r["landed"] | base_r["pinned"]) & r["dropped"], key=int
            )
            lines.append(
                f"    -> {label:<6} {sha[:10]}   "
                f"{len(freed)} unpinned / {len(newly_pinned)} newly pinned / "
                f"{len(newly_dropped)} newly dropped"
            )
            for name, group in (
                ("unpinned", freed), ("newly pinned", newly_pinned),
                ("newly dropped", newly_dropped),
            ):
                if group:
                    lines.append(
                        f"         {name}: " + " ".join("#" + str(n) for n in group[:12])
                        + (" …" if len(group) > 12 else "")
                    )
        lines.append("")
    lines.append(
        "  A PR that moves from 'pinned' to 'head' is one the advance actually"
    )
    lines.append("  frees. That is the number the in-isolation mode cannot report.")
    lines.append("")
    return "\n".join(lines)


def candidate_bases(repo, branch, pinned, count=4):
    """Pinned base, branch tip, and evenly spaced commits between them."""
    tip = git(["rev-parse", f"{branch}"], repo).strip()
    out = []
    if pinned:
        pinned_full = git(["rev-parse", pinned], repo).strip() or pinned
        out.append(("pinned", pinned_full))
        between = [
            c for c in git(
                ["rev-list", "--first-parent", f"{pinned_full}..{tip}"], repo
            ).split() if c
        ]
        between.reverse()  # oldest -> newest
        if between and count > 2:
            step = max(1, len(between) // (count - 1))
            for i in range(step, len(between) - 1, step):
                out.append((f"+{i}", between[i]))
    out.append(("tip", tip))
    # De-duplicate while preserving order.
    seen, uniq = set(), []
    for label, sha in out:
        if sha not in seen:
            seen.add(sha)
            uniq.append((label, sha))
    return uniq


def evaluate(repo, bases, refs):
    """{sha: set(pr numbers that merge cleanly)}"""
    result = {}
    for label, sha in bases:
        clean = {n for n in refs if merges_clean(repo, sha, f"refs/baseadv/{n}")}
        result[sha] = clean
        print(f"  {label:>8} {sha[:10]}  {len(clean):>4} / {len(refs)} merge clean")
    return result


def render(bases, results, refs, repo):
    lines = ["", "=" * 68, "Base advisor", "=" * 68, ""]
    best = max(results.items(), key=lambda kv: len(kv[1]))[0]
    for label, sha in bases:
        landed = results[sha]
        when = git(["log", "-1", "--format=%ci", sha], repo).strip()[:16]
        mark = "  <- most PRs land here" if sha == best and len(bases) > 1 else ""
        lines.append(
            f"  {label:>8}  {sha[:10]}  {when}   {len(landed):>4}/{len(refs)}{mark}"
        )
    lines.append("")

    # What moving the pin actually costs, pairwise against the current pin.
    first_sha = bases[0][1]
    if len(bases) > 1:
        base_set = results[first_sha]
        lines.append(f"  Relative to {bases[0][0]} ({first_sha[:10]}):")
        for label, sha in bases[1:]:
            gained = sorted(results[sha] - base_set, key=int)
            lost = sorted(base_set - results[sha], key=int)
            lines.append(
                f"    -> {label:<6} {sha[:10]}   +{len(gained)} / -{len(lost)}"
            )
            if lost:
                lines.append(
                    "         lost: " + " ".join("#" + n for n in lost[:12])
                    + (" …" if len(lost) > 12 else "")
                )
            if gained:
                lines.append(
                    "         gained: " + " ".join("#" + n for n in gained[:12])
                    + (" …" if len(gained) > 12 else "")
                )
        lines.append("")
    lines.append(
        "  A candidate that loses nothing is a free advance. PRs in a persistent"
    )
    lines.append(
        "  'lost' column are the ones whose authors would need to rebase."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Pick a base commit for a curation")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--repo", required=True, help="a clone of the upstream project")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--candidates", type=int, default=4)
    ap.add_argument(
        "--at", action="append", default=[],
        help="evaluate this commit-ish (repeatable); overrides --candidates",
    )
    ap.add_argument(
        "--in-stack", action="store_true",
        help="replay the curation in order instead of testing each PR against "
             "the base alone — slower, but the question the build actually asks",
    )
    args = ap.parse_args(argv)

    try:
        profile = bonsaipr_profile.load_profile(args.profile, verbose=False)
    except bonsaipr_profile.ProfileError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    numbers = sorted(profile.select_prs, key=int)
    if not numbers:
        print(
            "❌ This profile selects no explicit PRs, so there is nothing to "
            "evaluate a base against (an `everything` profile always takes "
            "whatever merges).",
            file=sys.stderr,
        )
        return 1

    print(f"profile {profile.name}: {len(numbers)} selected PRs")
    git(["fetch", "-q", args.remote, profile.base_branch], args.repo)

    try:
        if args.at:
            bases = [(a, git(["rev-parse", a], args.repo).strip() or a) for a in args.at]
        else:
            bases = candidate_bases(
                args.repo,
                f"{args.remote}/{profile.base_branch}",
                profile.base_commit,
                count=args.candidates,
            )
        print(f"evaluating {len(bases)} candidate base(s)\n")

        print("fetching PR heads…")
        refs = fetch_pr_heads(args.repo, [str(n) for n in numbers], remote=args.remote)
        missing = len(numbers) - len(refs)
        if missing:
            print(f"  ({missing} PR head(s) unavailable — closed or deleted fork)")
        if not refs:
            print("❌ No PR heads could be fetched.", file=sys.stderr)
            return 1
        print()

        if args.in_stack:
            recorded = [int(n) for n in (profile.data.get("order_seq") or [])]
            order = recorded + [n for n in numbers if n not in set(recorded)]
            results = evaluate_in_stack(
                args.repo, bases, refs, order, profile.pins
            )
            print(render_in_stack(bases, results, refs, args.repo))
        else:
            results = evaluate(args.repo, bases, refs)
            print(render(bases, results, refs, args.repo))
    finally:
        # Never leave scratch refs in someone's repository.
        cleanup_refs(args.repo)

    return 0


if __name__ == "__main__":
    sys.exit(main())

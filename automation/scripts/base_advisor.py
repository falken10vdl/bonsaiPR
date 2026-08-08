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
as upstream moves. This answers, for a given profile:

    at THIS base, how many of my selected PRs actually merge?

It never rebases, merges, or writes to the repository: every answer comes from
`git merge-tree --write-tree`, which performs a real three-way merge into the
object store and touches no working tree.

Reading the output
------------------
The interesting column is not the total, it is what moving the pin would cost.
"Advance the base" is cheap when a newer candidate loses nothing, and expensive
when it drops PRs the curation exists to carry. Contributors rebasing is what
makes a newer base cheap again - so a persistent loss column is a list of PRs
worth nudging, not a reason to stay pinned forever.

CLI
---
    python base_advisor.py --profile NAME --repo DIR [--candidates N]
    python base_advisor.py --profile NAME --repo DIR --at <commit> [--at <commit>]
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

        results = evaluate(args.repo, bases, refs)
        print(render(bases, results, refs, args.repo))
    finally:
        # Never leave scratch refs in someone's repository.
        cleanup_refs(args.repo)

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
bonsaipr_profile.py - Curation as a committed, shareable file.

Why this exists
---------------
RFC-001 s3.3: BonsaiPR already has a curation mechanism - USERNAMES, EXCLUDED
and SKIP_CPP_PRS in an untracked `.env`. What it does not have is a curation
that can be *named, versioned, shared, forked, diffed or cited*. Three
comma-separated strings on one machine cannot be any of those things.

A profile is that same curation as a file. Nothing about the merge logic
changes; this module only decides *which PRs go in* and hands the answer back
in exactly the shape `00_clone_merge_and_create_branch.py` already uses.

Backwards compatibility is absolute: with no profile configured, `load_profile()`
reads the same env vars as before and behaves identically. Nobody is forced to
migrate, and the canonical instance keeps running untouched.

Selection model (RFC-001 s4)
----------------------------
    select.mode = "everything"   all non-draft PRs, minus `exclude`  (today)
                | "allowlist"    only select.prs / select.authors

    exclude.prs      {"7098": {"why": ..., "reason": ..., "since": ...}}
    exclude.authors  [logins]
    exclude.drafts   bool
    exclude.cpp      bool        (maps to the existing SKIP_CPP_PRS behaviour)

    prefer  [[winner, loser], ...]   pairwise choice, NOT a rejection
    pin     {"7123": "8f09b96"}      freeze at a tested head

Exclusions carry reasons, and that is the point (RFC-001 s8.3): what a curator
*refuses* is more architecturally informative than what they accept. The format
therefore accepts three shapes, in increasing order of usefulness, and never
requires the richest one - a mandatory reason field would just fill up with
"n/a":

    [7098]                                    excluded, no reason
    {"7098": "bypasses the tool/ layer"}       excluded, free-text reason
    {"7098": {"why": "architecture", ...}}     excluded, categorized + dated

CLI
---
    python bonsaipr_profile.py show [NAME]     resolve and print a profile
    python bonsaipr_profile.py check [NAME]    validate, exit 1 on problems
"""

import os
import re
import sys
import json
import argparse

SCHEMA_VERSION = 1

PROFILES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "profiles"
)

MODE_EVERYTHING = "everything"
MODE_ALLOWLIST = "allowlist"
MODES = (MODE_EVERYTHING, MODE_ALLOWLIST)

# RFC-001 s4.2. Only `architecture` feeds the design signal; the rest are useful
# but are different kinds of statement, and blending them would be the easy
# mistake. Unknown values are kept (never silently dropped) but warned about, so
# the vocabulary can grow without this file becoming a gatekeeper.
WHY_CATEGORIES = ("architecture", "regression", "scope", "duplicate",
                  "performance", "unstable")
WHY_ARCHITECTURAL = "architecture"

ENV_PROFILE = "BONSAIPR_PROFILE"


class ProfileError(Exception):
    """Profile is malformed badly enough that guessing would be worse."""


# --------------------------------------------------------------------------- #
# Normalization
# --------------------------------------------------------------------------- #

def _as_int_set(values):
    out = set()
    for v in values or []:
        try:
            out.add(int(str(v).strip().lstrip("#")))
        except (TypeError, ValueError):
            continue
    return out


def normalize_exclusions(raw):
    """Accept all three exclusion shapes; return {int: {why, reason, since}}.

    Missing fields stay missing rather than being filled with placeholders - a
    consumer must be able to tell "no reason given" from "reason: none", which
    is the same zero-vs-unknown distinction federate.py's `unavailable` block
    protects.
    """
    out = {}
    if not raw:
        return out

    if isinstance(raw, (list, tuple, set)):
        for n in _as_int_set(raw):
            out[n] = {}
        return out

    if not isinstance(raw, dict):
        raise ProfileError(f"exclude.prs must be a list or object, got {type(raw).__name__}")

    for key, val in raw.items():
        try:
            num = int(str(key).strip().lstrip("#"))
        except (TypeError, ValueError):
            continue
        if val is None or val == "":
            out[num] = {}
        elif isinstance(val, str):
            out[num] = {"reason": val.strip()}
        elif isinstance(val, dict):
            rec = {}
            for f in ("why", "reason", "since"):
                if val.get(f):
                    rec[f] = str(val[f]).strip()
            out[num] = rec
        else:
            raise ProfileError(
                f"exclude.prs[{key}] must be a string or object, got {type(val).__name__}"
            )
    return out


def _normalize_prefer(raw):
    """[[winner, loser], ...] - a choice between two PRs, not a rejection."""
    pairs = []
    for item in raw or []:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ProfileError(f"prefer entries must be [winner, loser] pairs, got {item!r}")
        try:
            pairs.append([int(item[0]), int(item[1])])
        except (TypeError, ValueError):
            raise ProfileError(f"prefer entries must be PR numbers, got {item!r}")
    return pairs


def _normalize_pins(raw):
    pins = {}
    for key, sha in (raw or {}).items():
        try:
            pins[int(str(key).lstrip("#"))] = str(sha).strip()
        except (TypeError, ValueError):
            continue
    return pins


# --------------------------------------------------------------------------- #
# Profile
# --------------------------------------------------------------------------- #

class Profile:
    """A resolved curation, plus the compat surface the merge script expects."""

    def __init__(self, data, source="(env)", warnings=None):
        self.data = data or {}
        self.source = source
        self.warnings = list(warnings or [])

        select = self.data.get("select") or {}
        exclude = self.data.get("exclude") or {}

        self.name = self.data.get("name") or "(implicit)"
        self.description = self.data.get("description") or ""
        self.maintainer = self.data.get("maintainer") or ""
        self.inherits = self.data.get("inherits")

        self.mode = (select.get("mode") or MODE_EVERYTHING).strip().lower()
        self.select_prs = _as_int_set(select.get("prs"))
        self.select_authors = [a for a in (select.get("authors") or []) if a]

        self.exclusions = normalize_exclusions(exclude.get("prs"))
        self.exclude_authors = [a for a in (exclude.get("authors") or []) if a]
        self.exclude_drafts = bool(exclude.get("drafts", True))
        self.exclude_cpp = bool(exclude.get("cpp", False))

        self.prefer = _normalize_prefer(self.data.get("prefer"))
        self.pins = _normalize_pins(self.data.get("pin"))
        self.orders = self.data.get("orders") or []

    # -- compat surface: exactly what 00_clone_merge already consumes -------- #

    @property
    def users(self):
        """Author allowlist in the merge script's historical shape.

        That script uses `[""]` to mean "all authors", so preserve the idiom
        rather than making 950 lines downstream learn a new one.
        """
        return list(self.select_authors) if self.select_authors else [""]

    @property
    def excluded_prs(self):
        """Just the numbers - the merge script does not care about reasons."""
        return set(self.exclusions)

    @property
    def skip_cpp(self):
        return self.exclude_cpp

    # -- selection ---------------------------------------------------------- #

    def selects(self, pr_number, author=None):
        """Would this profile include the PR? (before conflict/draft handling)"""
        pr_number = int(pr_number)
        if pr_number in self.exclusions:
            return False
        if author and author in self.exclude_authors:
            return False
        if self.mode == MODE_ALLOWLIST:
            if pr_number in self.select_prs:
                return True
            return bool(author and author in self.select_authors)
        # everything: in unless explicitly out
        if self.select_authors and author and author not in self.select_authors:
            return False
        return True

    def architectural_objections(self):
        """Exclusions that state a design principle (RFC-001 s8.3)."""
        return {
            n: rec
            for n, rec in self.exclusions.items()
            if rec.get("why") == WHY_ARCHITECTURAL
        }

    def summary(self):
        bits = [f"profile={self.name}", f"mode={self.mode}"]
        if self.inherits:
            bits.append(f"inherits={self.inherits}")
        if self.mode == MODE_ALLOWLIST:
            bits.append(f"select={len(self.select_prs)}")
        if self.select_authors:
            bits.append(f"authors={len(self.select_authors)}")
        if self.exclusions:
            reasoned = sum(1 for r in self.exclusions.values() if r.get("reason"))
            bits.append(f"exclude={len(self.exclusions)} ({reasoned} with reasons)")
        if self.pins:
            bits.append(f"pinned={len(self.pins)}")
        if self.prefer:
            bits.append(f"prefer={len(self.prefer)}")
        if self.exclude_cpp:
            bits.append("skip-cpp")
        return "  ".join(bits)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def _profile_path(name, profiles_dir=None):
    base = profiles_dir or PROFILES_DIR
    if name.endswith(".json"):
        return os.path.join(base, name)
    return os.path.join(base, f"{name}.json")


def _read(name, profiles_dir=None):
    path = _profile_path(name, profiles_dir)
    if not os.path.exists(path):
        raise ProfileError(f"No such profile: {path}")
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f), path
        except ValueError as e:
            raise ProfileError(f"{path}: invalid JSON - {e}")


def _merge_parent(parent, child):
    """Shallow merge, child wins (RFC-001 s4).

    The parent's `select` is the starting set; the child's `select` and
    `exclude` are applied on top. This is what makes "whatever the canonical
    build ships, minus these three" expressible without restating 485 numbers
    that churn on every upstream change.
    """
    out = json.loads(json.dumps(parent))  # deep copy, parent is cached
    for key, val in (child or {}).items():
        if key in ("select", "exclude") and isinstance(val, dict):
            merged = dict(out.get(key) or {})
            for k, v in val.items():
                if k == "prs" and key == "exclude":
                    # Union exclusions rather than replacing: a child saying "also
                    # not this one" must not silently drop the parent's refusals.
                    base = normalize_exclusions(merged.get("prs"))
                    base.update(normalize_exclusions(v))
                    merged["prs"] = {str(n): r for n, r in sorted(base.items())}
                else:
                    merged[k] = v
            out[key] = merged
        else:
            out[key] = val
    out.pop("inherits", None)
    return out


def resolve(name, profiles_dir=None, _seen=None):
    """Load a profile and fold in its `inherits` chain. Returns (data, warnings)."""
    _seen = _seen or []
    if name in _seen:
        raise ProfileError(f"Circular inherits: {' -> '.join(_seen + [name])}")

    data, path = _read(name, profiles_dir)
    warnings = []

    schema = data.get("schema")
    if schema is not None and schema != SCHEMA_VERSION:
        warnings.append(
            f"{path}: schema {schema} (this loader speaks {SCHEMA_VERSION}); "
            f"unknown fields are ignored"
        )

    parent_ref = data.get("inherits")
    if parent_ref:
        # "owner/profile" is a federated reference (RFC-001 phase 2). Until peers
        # are fetchable, only the local part can be resolved - say so rather than
        # silently producing a different curation than the file asks for.
        if "/" in parent_ref:
            owner, _, local = parent_ref.partition("/")
            warnings.append(
                f"{path}: inherits '{parent_ref}' is a remote reference; phase 1 "
                f"resolves the local profile '{local}' only (peer fetch is phase 2)"
            )
            parent_ref = local
        parent_data, parent_warnings = resolve(
            parent_ref, profiles_dir, _seen + [name]
        )
        warnings = parent_warnings + warnings
        data = _merge_parent(parent_data, data)

    return data, warnings


def validate(data, source="(profile)"):
    """Non-fatal problems worth telling a curator about."""
    warnings = []
    select = data.get("select") or {}
    exclude = data.get("exclude") or {}
    mode = (select.get("mode") or MODE_EVERYTHING).strip().lower()

    if mode not in MODES:
        raise ProfileError(f"{source}: select.mode must be one of {MODES}, got {mode!r}")

    exclusions = normalize_exclusions(exclude.get("prs"))

    # RFC-001 s4.2: an exclusion only means anything relative to a baseline that
    # would have included it. On a bare allowlist the un-listed PRs are absent,
    # not rejected, so an exclude block there is nearly always a mistake - and,
    # worse, would publish rejections nobody made.
    if exclusions and mode == MODE_ALLOWLIST and not data.get("inherits"):
        warnings.append(
            f"{source}: exclude.prs is set on an allowlist profile with no "
            f"'inherits'. Un-selected PRs are already absent, so these "
            f"{len(exclusions)} exclusions assert rejections that were never "
            f"actually made. See RFC-001 s4.2."
        )

    for num, rec in sorted(exclusions.items()):
        why = rec.get("why")
        if why and why not in WHY_CATEGORIES:
            warnings.append(
                f"{source}: exclude.prs[{num}].why = {why!r} is not a known "
                f"category {WHY_CATEGORIES}; it will be carried but will not "
                f"feed the architectural signal"
            )
        if rec.get("since") and not re.fullmatch(r"[0-9a-fA-F]{7,40}", rec["since"]):
            warnings.append(
                f"{source}: exclude.prs[{num}].since = {rec['since']!r} does not "
                f"look like a commit sha; staleness cannot be checked"
            )
        if why and not rec.get("since"):
            warnings.append(
                f"{source}: exclude.prs[{num}] has a reason but no 'since' sha, so "
                f"the objection can never go stale. See RFC-001 s4.2."
            )

    if mode == MODE_ALLOWLIST and not (select.get("prs") or select.get("authors")):
        warnings.append(f"{source}: allowlist profile selects nothing")

    return warnings


def from_env(env=None):
    """The legacy curation, expressed as a profile.

    RFC-001 s4.1's compat table. Unset env vars produce exactly today's
    behaviour: everything, minus drafts.
    """
    env = env if env is not None else os.environ

    authors = [u.strip() for u in (env.get("USERNAMES") or "").split(",") if u.strip()]
    excluded = [x.strip() for x in (env.get("EXCLUDED") or "").split(",") if x.strip().isdigit()]
    skip_cpp = (env.get("SKIP_CPP_PRS") or "").strip().lower() in ("1", "true", "yes")

    return {
        "schema": SCHEMA_VERSION,
        "name": "(env)",
        "description": "Implicit profile synthesized from .env (RFC-001 s4.1)",
        "select": {"mode": MODE_EVERYTHING, "prs": [], "authors": authors},
        "exclude": {
            "prs": excluded,
            "authors": [],
            "drafts": True,
            "cpp": skip_cpp,
        },
    }


def load_profile(name=None, profiles_dir=None, env=None, verbose=True):
    """Resolve the active curation: named profile, or the legacy env vars.

    Never raises for a *missing* profile configuration - only for one that is
    present and malformed, where guessing would be worse than stopping.
    """
    env = env if env is not None else os.environ
    name = name or (env.get(ENV_PROFILE) or "").strip()

    if not name:
        data = from_env(env)
        profile = Profile(data, source="(env)")
    else:
        data, warnings = resolve(name, profiles_dir)
        warnings = warnings + validate(data, source=f"profiles/{name}.json")
        profile = Profile(data, source=f"profiles/{name}.json", warnings=warnings)

    if verbose:
        print(f"📋 Curation: {profile.summary()}  [{profile.source}]")
        for w in profile.warnings:
            print(f"⚠️  {w}")

    return profile


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="Inspect and validate BonsaiPR profiles")
    ap.add_argument("command", choices=["show", "check"])
    ap.add_argument("name", nargs="?", default=None)
    ap.add_argument("--profiles", default=None)
    args = ap.parse_args(argv)

    try:
        profile = load_profile(args.name, profiles_dir=args.profiles, verbose=False)
    except ProfileError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    print(f"{profile.summary()}   [{profile.source}]")
    if profile.description:
        print(f"   {profile.description}")

    if args.command == "show":
        print()
        print(f"  mode            {profile.mode}")
        print(f"  users           {profile.users}")
        print(f"  excluded_prs    {sorted(profile.excluded_prs) or '—'}")
        print(f"  skip_cpp        {profile.skip_cpp}")
        if profile.pins:
            print(f"  pins            {profile.pins}")
        if profile.prefer:
            print(f"  prefer          {profile.prefer}")
        arch = profile.architectural_objections()
        if arch:
            print(f"\n  architectural objections ({len(arch)}):")
            for num, rec in sorted(arch.items()):
                stale = f" @{rec['since']}" if rec.get("since") else ""
                print(f"    #{num}{stale}: {rec.get('reason', '(no reason)')}")

    for w in profile.warnings:
        print(f"⚠️  {w}")
    return 1 if (args.command == "check" and profile.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())

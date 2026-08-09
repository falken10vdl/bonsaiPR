# Proposals

Design proposals for the BonsaiPR build system. These are **discussion documents,
not documentation** — a proposal describes something that does not exist yet, and
may never exist. For how the system works today, see the root
[`README.md`](../README.md) and [`automation/README.md`](../automation/README.md).

Each proposal is numbered `RFC-NNN` and keeps that number for life, so a link to it
stays valid even after it is accepted, rejected, or superseded.

**Statuses:** `Draft` (open for comment) · `Accepted` (agreed, may not be built yet) ·
`Rejected` (with the reasoning kept, so it is not re-proposed from scratch) ·
`Superseded by RFC-NNN` · `Implemented`

---

## RFC-001 — [Federated Curated Builds](RFC-001-federated-curated-builds.md)

📄 **Non-technical summary:** [RFC-001 — Plain-Language Version](RFC-001-federated-curated-builds_plain-language.md).
Same idea without the jargon; the one to hand someone who has ten minutes. Kept
current alongside the work.


**Status:** Draft · **phases 0–3 implemented** — see falken10vdl/bonsaiPR#11 and
`docs/dev-notes/rfc-001-federation.md`

**What it proposes:** Let people publish their own *curated* BonsaiPR builds instead
of everyone sharing one build containing every PR, and aggregate those curations into
a per-PR signal — *"selected by 6 of 9 independent curators, merged cleanly for 42
days, conflicts only with #7098"* — that an upstream maintainer can actually act on.

Four parts: a **profile** (a curation as a committed, forkable file), a **manifest**
(a build declaring who produced it and under what curation), a **peer list** (who you
aggregate), and a **`distill`** command that reverse-engineers a profile out of the
hand-maintained build branches powerusers already keep.

**Why it might matter even if the federation idea goes nowhere:** measuring one real
poweruser branch found that 100% of its 160 integration merges are mechanically
attributable to open PRs, and that it carries 81 commits of the curator's own feature
work — much of which upstream has never seen.

**Open questions needing a decision:** whether the peer list is canonical or
per-curator; whether the canonical instance should build a fourth "recorded" merge
order; and whether IfcOpenShell upstream wants the maintainer digest at all. (The
profile format question is settled — JSON, for consistency with `index.json` and
`state.json`, and no dependency.)

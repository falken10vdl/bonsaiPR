# A Network of Curated Builds — Plain-Language Version

*A proposal for how a community can work together to decide which improvements to a piece of software are actually worth keeping.*

> **What this is.** A non-technical companion to
> [RFC-001](RFC-001-federated-curated-builds.md). Same idea, no jargon, no code.
> Read this one first; read the RFC if you need the mechanics.
>
> **Kept current as the work proceeds** — see [Keeping this honest](#keeping-this-honest)
> at the end. Last brought up to date: **2026-08-09**.

---

## A quick note on the words

This document is about improving a program called **Bonsai**, which architects use to produce building documentation. You don't need to know anything about programming to follow it. A few plain definitions will carry you through:

- A **change** (or "contribution") is one specific improvement someone proposes — a bug fix, a new feature, a tweak. Think of it as a single suggested edit to the program.
- A **build** is a working copy of the program assembled from a particular set of changes. Different builds contain different sets of changes.
- To **include** a change in a build is to actually fold it in. Sometimes two changes clash and can't both go in — like two people editing the same sentence in a shared document in incompatible ways.
- **Curation** is the act of choosing which changes go into a build and which stay out.
- The **base** is the version of the program you start from before folding anything in. It matters more than you'd expect, for reasons in [§6](#6-the-discovery-nobody-expected-most-broken-changes-arent-broken).

That's the whole vocabulary. Everything below is about who does the choosing, and how their choices can be pooled into useful knowledge.

---

## 1. The problem: choosing is now harder than making

Something has quietly shifted in how open-source software gets built. Writing a plausible improvement used to be the expensive part — it took a skilled person real hours. With modern AI tools, producing a change that *looks* reasonable is nearly free. Anyone can generate one in minutes.

What has *not* gotten cheaper is the judgment call: **does this change actually belong in the program?** Is it built the right way? Will it hold up? Does it fit with everything else? That decision still takes a knowledgeable human, and it lands on the smallest group in any project — the handful of maintainers who guard quality.

So the bottleneck moved. It used to be *making* things. Now it's *choosing* among the flood of things people (and their AI assistants) make. This document is about relieving that bottleneck by spreading the choosing across many people and then combining what they decide.

Bonsai is simply where the numbers happen to be in front of us. As of early August 2026, there were **847 proposed changes** waiting for a decision. Of those, about 450 fit into any build without trouble, roughly 180 fit in some arrangements but not others, and about 210 don't fit at all. Every one of the first two groups *might* be worth keeping — and the only evidence anyone has for most of them is the change itself and a few offhand comments.

---

## 2. What happens today, and what could happen instead

Today, the project produces **one build for everyone**. A tool called BonsaiPR gathers up essentially every proposed change and bundles them together, and that single bundle is what people download. Everyone gets everything.

That's a reasonable starting point, but it wastes something valuable. Experienced users are *already* making private judgment calls about which changes they trust — they just keep those calls to themselves, buried in their own personal setups.

The proposal is this: **let people publish their own curated builds, and combine those curations into a shared signal.** Instead of one bundle, imagine nine different experts each publishing their own carefully chosen selection. When six of those nine independently choose the same change — without ever talking to each other — that agreement means something.

Here's the kind of statement this would let a maintainer see about a proposed change:

> *Chosen by 6 of 9 independent curators. Fit cleanly into 14 builds in a row over 42 days. Only clashes with one other change. Nobody who picked it has since dropped it.*

Compare that to what a maintainer has today: three people typing "looks good to me." The first is a genuinely different, and far stronger, kind of evidence.

---

## 3. Three things people would publish

The whole system rests on three simple published documents. None of them is complicated; the point is just to write down, plainly and publicly, things people currently keep in their heads.

### The Profile — "here is my selection"

A **profile** is a named, written-down curation. It says, in effect: *"This is my build of Bonsai. It's for production architectural documentation. Here are the changes I include, here are the ones I deliberately leave out, and here's why."*

The important thing is that a profile is a real, shareable, public document — something a person maintains and becomes known for, the way a playlist maker or a magazine editor is known for their taste. Right now these curations exist only as scattered private settings that can't be named, shared, compared, or pointed to. Turning them into published documents is most of the whole idea.

A profile can also **inherit** from another. The most common case is "give me whatever the standard build ships, but leave out these three changes." That way a curator doesn't have to re-list hundreds of items every time — they just note their differences from a starting point.

### The Manifest — "here is what I actually built, and who I am"

A **manifest** is the record a curator publishes after building. On its own, "this change fit cleanly" tells you nothing useful — you need to know *who* built it, *from what starting point*, and *under which curation*. The manifest attaches that identity to the results. It's the difference between an anonymous review and a signed one.

### The Peer list — "here is whose choices I'm listening to"

A **peer list** is simply the set of curators whose published choices you gather up. Crucially, there's no central authority and no master list. You choose whom to listen to. Different people can listen to different sets of curators and that's fine — it's a subscription, like following people whose taste you respect, not a registry you have to be admitted to.

---

## 4. Turning existing work into a profile automatically

There's an obvious objection: *nobody is going to sit down and hand-write a list of 160 changes.* True. But here's the thing — experienced users are **already maintaining exactly that list**, without realizing it. They've spent months assembling their own personal build, adding this change and that one, tweaking as they go. That personal build *is* a curation. It's just messy, private, and undocumented.

So the main way a profile should come into existence is not by writing one, but by **automatically extracting one from a personal build somebody already has.** A tool walks through the history of that build, works out which proposed change each addition corresponds to, and produces a clean, published profile from it.

When this was tested on one real user's personal build, two things stood out.

**First, the extraction is remarkably reliable.** The build contained 160 deliberate additions, and the tool correctly matched **every single one** back to a specific proposed change. This isn't guesswork — the user had, without meaning to, labeled their work clearly enough that a simple automatic process could read it.

**Second — and this was a genuine surprise — the personal build also contained 81 pieces of original work the user had never shared with anyone.** These weren't housekeeping. They were real, substantive features: tools for sharing annotations across drawings, filters for linked models, and more. Some had been offered to the wider project elsewhere; some had never been offered at all. They'd simply been sitting in one person's private build, invisible to everyone else.

That reframes the whole feature. It isn't just a way to create profiles. It's a way to **discover valuable work that already exists and was never shared.** Even if the larger idea in this document went nowhere, surfacing those 81 hidden contributions would justify the effort on its own.

There are honest limits. This automatic extraction can't perfectly reproduce the original build, because the underlying changes keep evolving after they were first added — so the tool produces a "here's what's different now" report rather than a guarantee. And it works best on builds assembled in a tidy, consistent way; a chaotic build is harder to read. The tool is upfront about how confident it is in each case, and never publishes anyone's private work automatically — a human has to opt each piece in, one at a time.

---

## 5. What the combined data can tell you (and what it can't)

Once curators publish their choices, a tool pools them together and produces a set of **signals** about each proposed change. The single most important design principle here is that **each signal is honest about its own limits.** A signal that people over-read is worse than no signal at all.

A few examples of what gets measured:

- **How many independent curators chose this change** — a measure of deliberate demand. (Note: this tells you people *wanted* it, not that it *works*.)
- **How many builds it fit into cleanly** — a measure of whether it plays well with others. (Not the same as whether it does the right thing.)
- **How long it has kept fitting, build after build** — a measure of whether it has survived the program changing underneath it. (Not proof there are no hidden bugs.)
- **What it clashes with** — naming the specific other change it collides with, which points at a real, fixable problem.

The thing being measured here is subtle but important, so it's worth naming precisely. Committees and votes measure **consensus** — *we discussed this and agreed.* This system measures something different and stronger: **independent agreement** — *we never spoke, and we each arrived at the same place anyway.* It's the same reason independent replication counts for more than committee endorsement in science: nobody talked anybody into it. It's also the only kind of agreement you can realistically get from volunteers scattered across the world who will never all attend the same meeting.

One deliberate honesty runs through everything: the tool distinguishes *zero* from *unknown*. If a signal can't be computed yet, it says so plainly rather than showing a misleading "zero."

### The one big caveat

None of these signals measures whether the resulting program actually does the *right thing*. They measure whether a change fits and keeps fitting — not whether it behaves correctly. A change can slot in perfectly for six months and still be subtly wrong. This limitation is stated on every report the system produces, never buried. Two future additions could narrow the gap: curators vouching for changes they've used in real production work, and curators publishing the results of their own testing.

---

## 6. The discovery nobody expected: most "broken" changes aren't broken

This wasn't in the original proposal at all. It emerged from actually building the thing, and it may be the most immediately useful finding in the whole effort.

When a proposed change "doesn't fit," the natural assumption is that something is wrong with the change. Usually there isn't. **The ground moved underneath it.**

Here's what happens. Someone writes an improvement against the program as it stood in July. Over the following month the program itself changes — hundreds of small edits from everyone else. By August, the improvement no longer slots in cleanly. Nothing about it got worse. It's being fitted against a different program than the one it was written for.

This was measured directly. Taking one curator's set of 160 chosen changes and trying to fit them against successively newer starting points:

| starting point | changes that fit |
|---|---:|
| the one the curator originally used (July 7) | **158 of 160** |
| one week later | 151 |
| one month later (the newest available) | 141 |

Roughly **seventeen changes lost per month of drift** — and notably, moving to a newer starting point gained *nothing*. Not a single change fit better on newer ground.

The fix is straightforward: let a curator **pin** their starting point, rather than always being dragged to the newest one. A curated build then keeps working without asking every contributor to constantly redo their work. The cost is real but different — a pinned build stops receiving the program's own fixes, so the pin has to be moved forward deliberately, and there's a tool that reports exactly what moving it would cost.

Two refinements came out of using this:

**The starting point and the changes have to move together.** Pinning the starting point but letting the individual changes drift forward — or the reverse — is worse than doing neither. Old changes on new ground is the worst combination of all. They have to stay consistent, which is exactly why a Linux distribution ships a coherent *set* of versions rather than the newest of everything.

**When a change breaks, fall back rather than dropping it.** If a contributor's latest version no longer fits, the build quietly uses the last version the curator had verified — and says so in its report, along with how far behind that version now is. The build keeps working, *and* the report doubles as a list of contributors worth telling that their work has stopped fitting. That distance matters, and it is measured in the change's *own* work rather than in everything that has happened upstream since. On the current build most are one to three commits behind — nothing to act on — while one has moved 47 commits, which is a genuine gap worth closing. In practice this took one real build from 117 changes included to 128.

---

## 7. The most valuable idea in the whole proposal

If there's one thing worth defending hardest, it's the smallest one: **recording *why* a curator chose to leave a change out.**

Here's the reasoning. There's a fair criticism of this entire proposal — that pooling people's choices can only ever *rank the things people already made.* It can't produce the thing nobody proposed: the better approach, the insight that "this is the wrong way to do it, do it the other way." Combining what people *include* tends to produce coherence — things that work together survive together — which looks like good design from a distance but isn't quite the same thing.

Combining what people *reject*, with their reasons, gets much closer to the real thing. And the reason is simple: **including something says it's useful. Rejecting something usually says something about principle.** Nobody throws a perfectly working change out of their own build without holding some view about how the software *ought* to be put together. A rejection with a stated reason is compressed design wisdom.

And notice — almost every signal open-source software collects today (stars, downloads, thumbs-up) is *positive only.* The more informative half of the record, the "no, and here's why," is the half nobody keeps.

The interesting output isn't a count of rejections. It's a recurring *reason*. Imagine a report like:

> *Change #8123 — set aside by 5 curators. Three of them give the same architectural reason: it takes a shortcut that bypasses the program's proper structure. One says it's simply outside their build's focus. One gives no reason.*

Three independent people rejecting the same change *for the same architectural reason* is a design principle being **discovered** rather than **decreed** — and it costs nobody a meeting. That's exactly the kind of guidance a maintainer, a newcomer, or an AI reviewer all need.

Making this work fairly takes real care, and the proposal is careful:

- **An objection expires when the problem is fixed.** Every rejection is recorded against the exact version it was made about. Once the change is improved past that point, the objection goes stale and stops counting until someone renews it. Otherwise a fixed problem would follow a contributor around forever — the difference between an honest signal and a grudge.
- **Nothing is shown publicly on a single objection.** One person leaving something out is an opinion, not a signal, and publishing it against a named person's work would mostly just be a way to hurt people. It takes two or more independent curators before anything appears.
- **A reason is encouraged, never required,** because a mandatory reason field would just fill up with "n/a."
- **The system never scores a *person*.** It surfaces reasons about *changes*, quoted accurately with attribution — never a ranking of who's good.

The honest limitation: this only surfaces a principle *after* enough people have independently hit the same wall. Good design advice is most valuable *before* the work, not after. It's a lagging indicator — real, but late.

---

## 8. Keeping it honest: trust and gaming

Any system that aggregates opinions can be gamed. The obvious attack here: create fifty fake identities, have each one "choose" your pet change, and manufacture the appearance of consensus. The design steers around this rather than pretending it away.

The most important defense is simple: **count people, not builds.** Someone running their build a hundred times a day still counts as exactly one voice. And because there's no central list to inject yourself into — you appear in someone's aggregate only because *they* chose to listen to you — fake identities cost nothing to create and gain nothing without genuine adoption. On top of that, curators whose choices are near-identical to someone else's add little new information and can be weighted down accordingly, and every published summary must name exactly whose opinions it's based on. A claim of "6 of 9 curators" is meaningless without naming the 9.

The design doesn't pretend it can stop a determined bad actor from publishing a dishonest record. What it does is make dishonesty **attributable** — every published record names its author and can be checked against what they claim — and leaves the consequences social.

---

## 9. What's actually been built so far

This is no longer a proposal on paper. As of early August 2026 a **second curated build is running in public**, publishing its choices, and the pooling tool combines it with the original everything-build automatically.

Concretely, what exists:

- **A working curated build.** One curator's personal build was automatically converted into a published profile of 160 chosen changes, and that profile can be rebuilt on demand to record which changes still fit. The most recent build folded in **128 of the 129 chosen changes that are still open** — up from 117 before the starting-point fix in [§6](#6-the-discovery-nobody-expected-most-broken-changes-arent-broken).
- **Downloadable results, published on purpose.** The build produces installable versions for Windows, macOS and Linux — several have now been published — under the curation's own name so a subscriber knows which selection they're installing rather than just whose computer produced it. Nothing here happens on a timer. Rebuilding the record and publishing a version are both things a curator chooses to do — the second especially, since it says "this selection is worth installing." An interesting side effect: because the record only updates when the curator builds, it measures what that curator actually experiences, rather than what happened at 3am between two runs nobody looked at.
- **Pooling across two publishers, automatically.** The tool fetches both publishers' published records and combines them. **Seventeen changes currently disagree** — sixteen that the curated build can carry and the standard build cannot, one the other way. That disagreement is precisely the information the whole system exists to surface.

Running it also surfaced lessons worth recording, because they say something about the state of this kind of software generally.

**Seven latent faults, all invisible until someone else ran it.** The original tool had been run by exactly one person on one computer for its whole life. The moment a second person ran it, seven separate assumptions about *that particular computer* surfaced — a hard-coded home directory, a hard-coded web address, a check that only worked if a folder already existed. None of them had ever been wrong before. All of them were wrong immediately. That's a general lesson about single-operator software rather than a criticism of this one.

**Two of those seven produced a perfectly successful build that was silently wrong.** One assembled 129 changes onto the *wrong version* of the program and reported complete success. Another produced a correct build and then labelled it with the wrong name. Neither would have been caught by checking whether the process succeeded — you had to check what it actually produced. This is the strongest argument in the whole effort for publishing detailed records rather than pass/fail results.

**One early measurement was confidently, precisely wrong.** A first version accidentally mixed together separate histories and reported that a change had held up across 376 builds — when only 140 builds had ever happened. The fix was to keep each history separate. A wrong number that looks authoritative is more dangerous than an obvious gap, which is why several claims in this document were re-measured rather than carried forward on trust. Two were corrected as a result.

---

## 10. The honest risks

No proposal is worth much without naming how it could go wrong. The main ones:

- **The signal is weak until curation is selective.** As long as everyone includes everything, "included" carries no information. This is why the profiles and the pooling have to ship together — one is useless without the other — and it means the first several months of data will be thin. **This is still the largest open question:** there is currently one genuine curator and one everything-build, so the "how many people chose this" signal remains close to meaningless until somebody else publishes a selection.
- **Curator burnout.** This creates a new role. If maintaining a curated build isn't meaningfully easier than the messy private alternative, nobody will do it. Inheriting from a starting point keeps the ongoing cost low, and the automatic-extraction tool removes the up-front cost by generating a first profile from work people already have.
- **Good design is often unpopular, and this partly measures popularity.** Saying no to a well-liked feature because it's built the wrong way is exactly the maintainer's job — and a system built on adoption will systematically under-rate whoever does it. The "reasons for rejection" idea is a partial hedge, because it rewards articulating an unpopular principle rather than accumulating agreement. But it's a hedge, not a cure, and anyone building reports from this should resist the temptation to rank *people*.
- **Rejection reasons could become noise, or weapons.** Free text invites unkindness. The guards — reasons that expire when fixed, a two-person threshold before anything is shown, accurate attributed quoting, and never scoring a person — matter here, and the parts that touch a named contributor's work should always have a human look before anything is published.
- **Fragmentation.** Nine curated builds mean nine slightly different programs, which can make problem reports harder to sort out. This is softened by the fact that every build now carries a clear published record of exactly what's in it — arguably better than today.
- **A pinned build going stale.** Pinning the starting point ([§6](#6-the-discovery-nobody-expected-most-broken-changes-arent-broken)) keeps a curation working, but a curator who pins and never looks again is running increasingly old software. Pinning *while watching the cost of moving forward* is the healthy version; there's a tool for exactly that, but it only helps if someone runs it.

There's also a larger, quieter risk worth stating plainly. A public, ongoing record of who curates well will probably change *how people earn trusted positions* in a project. Today that path runs on visibility and personal relationships — which is slow, tends to reproduce the existing group's blind spots, and depends on someone influential noticing you. A public track record makes that process answer to something more visible. That's genuinely a good thing in many ways. It's also the design's most obvious way to go wrong, because *the moment standing confers anything, it becomes worth gaming.* It's tracked as a risk to watch, not claimed as a win.

---

## 11. In one paragraph

The core idea is this: let people publish their own carefully chosen versions of a shared program, along with a clear record of what they chose and why — then pool those independent choices into a signal about which changes, and which *combinations* of changes, genuinely hold up. Most of the machinery to do this already exists; what's new is simply naming each person's curation and publishing who made it. That's what turns Bonsai from *one build everybody shares* into *a network of curated builds whose agreement actually means something.*

The single field worth defending hardest is the smallest one — a **reason attached to a rejection.** Counting what people include measures usefulness. But nobody throws a working change out of their own build without a view about how the software ought to be built, and three people independently rejecting the same change for the same reason is a design principle being discovered rather than decreed. It costs nobody a meeting, and it captures the half of the record that everyone else throws away.

---

## <a id="keeping-this-honest"></a>Keeping this honest

This document is **maintained alongside the work**, not written once. It is the
executive summary — the thing to hand someone who has ten minutes — so a stale
claim here misleads more people than a stale claim anywhere else in the repo.

**What changes and what doesn't.** Sections 1–5, 7 and 8 are the argument; they
change only if the design changes. Sections 6, 9 and 10 carry measurements and
status, and go out of date on their own.

**When to update it.** Whenever a number quoted here is re-measured, whenever a
phase completes, and whenever something is learned that would change a reader's
mind. Update the date at the top when you do.

**Where the detail lives.** [RFC-001](RFC-001-federated-curated-builds.md) holds
the design and the evidence;
[`docs/dev-notes/rfc-001-federation.md`](../docs/dev-notes/rfc-001-federation.md)
holds the working state. This file should never be the only place a fact appears —
if it is, it belongs in one of those and a plain-language version belongs here.

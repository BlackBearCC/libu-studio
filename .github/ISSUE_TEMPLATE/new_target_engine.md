---
name: New target engine
about: Propose adding support for a new consuming engine (Unity, Cocos, Spine, ...)
title: "[target] add support for <engine>"
labels: target-engine, enhancement
---

## Engine

<!-- Unity 2022.3 LTS / Cocos Creator 3.8 / Spine 4.2 / browser Canvas / ... -->

## Asset format that engine wants

<!-- e.g. PNG sequence + atlas JSON, ATC compressed, KTX2, Spine .skel ... -->

## Manifest shape

<!-- Does it need a manifest.json equivalent? What fields? Can it be generated
     from `lab.db`'s anim_tasks + target_inject rows? -->

## Adapter scope

The new adapter typically needs:

- [ ] `skills/libu-gen/references/target-inject-<engine>.md` describing the
      hook-up steps inside the consuming project
- [ ] A new variant of `scripts/export-manifest.py` (or a flag) for that
      manifest format
- [ ] An entry in `SKILL.md`'s pipeline index
- [ ] (Optional) sample target project layout in `examples/<engine>/`

## Willing to maintain it?

Target engines need somebody who actually uses the engine on a real project,
otherwise drift is fast. Please indicate:

- [ ] I have a production project on this engine and will keep the adapter alive
- [ ] I have a hobby project; happy to update it sometimes
- [ ] Proposal only — looking for someone else to own it

# Character: `<your-slug>`

> Template — copy this file to `<your-slug>.md` and fill in for your character.
> The file is loaded by the `libu-gen` skill **before any prompt is written**,
> so the agent can lock in visual identity and tone before calling liblib.

| Field | Value |
|---|---|
| `slug` | `<your-slug>` |
| `display_name` | `<Display Name>` |
| target project | `<path to your consuming project>` |
| `inject_target_dir` | `<relative path inside target project, e.g. apps/godot-pet/assets/character-design/<slug>/anim/>` |
| controller | `<path to character-controller source, if applicable>` |
| reference frame | `<path to a real shipped frame to anchor visual ground truth>` |

## Visual

Describe what the character looks like in 1-3 sentences. Hair / eyes / outfit /
proportion. **Do not** copy this description into liblib prompts; identity is
anchored by the reference image, not by words. This section is for the agent
to keep itself honest about what "looks right" means when reviewing output.

## Personality / Vibe

What is this character emotionally? List the adjectives that **must** appear
in animation prompts. The agent uses these to filter every generated prompt
before submission.

Examples (replace these with your own):

- **Must include at least one of**: `<adjective_1>`, `<adjective_2>`, `<adjective_3>`
- **Default hand position**: `<idle hand pose>`
- **Default expression**: `<idle expression>`
- **Banned words** (unless the animation specifically inverts the trope):
  `<word_1>`, `<word_2>`, ...

## Existing animation vocabulary

What is already shipped? New animations must "fit" into this vocabulary
without feeling out of place. List the existing ones with one-line vibe
descriptions:

- `<existing_anim_1>`: `<vibe>`
- `<existing_anim_2>`: `<vibe>`
- `...`

## Current idle probability distribution

If your character has a randomized idle pool (e.g. via
`character_controller._do_idle_action`), document the current weights so a new
idle knows where to insert itself.

> The source of truth is the controller code — grep it before trusting this
> file, since prose drifts faster than code.

## Attribute-driven animations (optional)

If the character has attribute-based states (hunger, mood, energy, ...):

- `<attribute>` levels: `<level_1>` / `<level_2>` / `...`
- Per-level idle bias rules
- Transition pairs and which frame they anchor to

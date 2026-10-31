#  characters

A small storybook roster you can drop onto map pins, squad rows, empty states, and onboarding. The tone is Fly.io-adjacent — watercolor, ink line, pastel sky — but these are **original sports creatures**. Do not use Fly.io’s logo, Fankie, or Annie Ruygt drawings.

Use a character when a player has no photo, for youth/casual teams, or as the product mascot layer. If someone has a real photo, prefer the photo in the pin and keep the rest of the Rally UI.

Art files live in `public/characters/`. Identity colors match `DESIGN.md`.

---

## Style bible (for more art later)

- Square crop, face readable at **48px** (map pin) and **52px** (sheet row)
- Watercolor wash + fine ink outline, no 3D, no photorealism
- Pastel grounds: lavender, peach, mint, cream
- Kit is simple (jersey, gloves, bib, whistle) — no real club crests
- Friendly, slightly odd, never aggressive
- One creature = one job on the team

Prompt seed:

> Square character portrait, original sports mascot. [creature] wearing [kit], watercolor and fine black ink outlines, pastel [color] background, whimsical storybook illustration, friendly, no text, no logo.

---

## The starting XI (plus staff)

### Pip — Captain · 9

![Pip](public/characters/pip.jpg)

| | |
|---|---|
| File | `public/characters/pip.jpg` |
| Creature | Peach fox |
| Color | `#E8A07A` |
| Status default | On the pitch |
| Voice | Short, sure, already there |

The one you look for first on the map. Give Pip to the organizer, skipper, or whoever created the team.

---

### Nim — Keeper

![Nim](public/characters/nim.jpg)

| | |
|---|---|
| File | `public/characters/nim.jpg` |
| Creature | Teal heron |
| Color | `#5BB8B0` |
| Status default | Warming up |
| Voice | Quiet, early, stretching in the box |

Use for keepers, last-back, or anyone who arrives first and waits.

---

### Bolt — Midfield

![Bolt](public/characters/bolt.jpg)

| | |
|---|---|
| File | `public/characters/bolt.jpg` |
| Creature | Mustard lightning blob |
| Color | `#E3B341` |
| Status default | En route (show `km/h` on the pin) |
| Voice | Always moving, never late in their own mind |

The live pin. Best for people still on the way.

---

### Moss — Fullback

![Moss](public/characters/moss.jpg)

| | |
|---|---|
| File | `public/characters/moss.jpg` |
| Creature | Sage turtle in a cap |
| Color | `#7BA86A` |
| Status default | At the gym |
| Voice | Slow to leave the house, reliable once there |

Use for defensive players, “see you after work,” gym-before-kickoff types.

---

### Kite — Wing

![Kite](public/characters/kite.jpg)

| | |
|---|---|
| File | `public/characters/kite.jpg` |
| Creature | Coral rabbit |
| Color | `#E8899A` |
| Status default | En route |
| Voice | Light, a bit late, coming down the path |

Use for wingers, runners, last to confirm.

---

### Marlow — Coach

![Marlow](public/characters/marlow.jpg)

| | |
|---|---|
| File | `public/characters/marlow.jpg` |
| Creature | Owl in a violet tracksuit |
| Color | `#7EA7D6` |
| Status default | On the pitch |
| Voice | Calm, clipboard energy, kickoff is sacred |

Use for coaches, managers, or the adult who books the pitch. Fine as a non-playing map pin.

---

### Patch — Physio

![Patch](public/characters/patch.jpg)

| | |
|---|---|
| File | `public/characters/patch.jpg` |
| Creature | Cream hedgehog with mint tape |
| Color | `#A78BFA` |
| Status default | At the gym |
| Voice | Gentle, “tape first, then we see” |

Use for physio, trainer, or a player tagged injured. If you add an `injured` chip later, Patch is the empty-state for that list.

---

### Nook — Bench

![Nook](public/characters/nook.jpg)

| | |
|---|---|
| File | `public/characters/nook.jpg` |
| Creature | Lavender cat in a bib |
| Color | `#C4B5FD` |
| Status default | Warming up |
| Voice | Half-asleep, ready if you ask twice |

Use for substitutes, maybe-coming, or RSVP = waitlist.

---

### Pipkin — Ball kid / sprite

![Pipkin](public/characters/pipkin.jpg)

| | |
|---|---|
| File | `public/characters/pipkin.jpg` |
| Creature | Apricot cloud-sprite with a corner flag |
| Color | `#F2C4A0` |
| Status default | On the pitch |
| Voice | Helpful, slightly lost, always at the flag |

Use for empty states, first-run, “invite your squad,” or a venue pin companion — not usually a real player.

---

### Reed — Referee

![Reed](public/characters/reed.jpg)

| | |
|---|---|
| File | `public/characters/reed.jpg` |
| Creature | Slate badger, yellow shirt, whistle |
| Color | `#5E537C` |
| Status default | En route |
| Voice | Fair, brief, kickoff is 7:00 exactly |

Use only if the match has an official. Otherwise keep Reed off the squad map so the team still feels like a team.

---

## How to assign them

1. If the player has a photo → pin uses the photo, character unused.
2. Else hash `playerId` through this list (skip Reed unless role is referee; skip Pipkin unless empty state):
   1. Pip  
   2. Nim  
   3. Bolt  
   4. Moss  
   5. Kite  
   6. Marlow  
   7. Patch  
   8. Nook  
3. Keep the **same character + color for that person forever** in a team (the identity-color rule in `DESIGN.md`).
4. Suggested role mapping if you want it to feel authored, not random:

| App role | Character |
|---|---|
| Captain / organizer | Pip |
| Keeper / last back | Nim |
| Midfield / always moving | Bolt |
| Defence / gym-before-game | Moss |
| Wing / runner | Kite |
| Coach / manager | Marlow |
| Physio / injured | Patch |
| Sub / waitlist | Nook |
| Empty state / invite | Pipkin |
| Referee | Reed |

---

## Usage in UI

- **Map pin:** 48px circle, 3px white ring, identity-color halo when selected.
- **Squad row:** 52px circle.
- **Player detail:** 72px circle next to Fraunces name.
- **Team switcher:** stack 3 avatars (Pip, Nim, Bolt) for the Night Owls-style mark.
- Do not put names on the pin. Character + color is the scan.

Sky wash for the map (not a character, but same world): `public/art/pitch-sky.jpg`.

---

## What not to do

- Don’t redraw Fly.io’s balloon-leader or copy their site illustrations.
- Don’t mix these with neon esports mascots or photoreal players on the same map.
- Don’t reuse one character for two people in the same team.
- Don’t give two teammates the same identity color.

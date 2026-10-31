# Rally — Sports Map UI & UX Spec

Give this file to an agent and ask it to **refactor the sports app to match this design**. Do not rebuild Rally as a demo. Apply this language, layout, and visual system to the existing product: real teams, real players, real venues, existing navigation and data.

This spec mixes two references:

- **UX structure** from a family-locator map: full-bleed map, identity-colored pins, team switcher, draggable bottom sheet, tap-to-detail.
- **Visual world** inspired by Fly.io: lavender canvas, deep violet ink, electric violet pills, editorial serif headlines, watercolor/ink characters. Do **not** copy Fly.io logos, Fankie, or Annie Ruygt illustrations. Create original sports characters in that storybook register.

---

## 0. Agent brief

### Goal

Make the sports app feel like opening a map of your squad before kickoff: you see who is already at the pitch, who is still on the way, and you can switch teams without leaving the map.

### What to keep from the existing sports app

- Domain data: teams, players, fixtures, venues, auth, real locations.
- Any flows that are not visual chrome (payments, chat backends, admin).
- Existing routing unless a screen is clearly a dashboard-that-should-become-a-map.

### What to change

- Home is a **map**, not a feed, list, or stats dashboard.
- Chrome floats over the map (team pill, sheet, filters).
- Players are identified by **character + color**, not by reading a table of names first.
- Status is sports language (`On the pitch`, `En route`), not generic “online / last seen.”
- Visual system is lavender / violet ink / serif titles. Drop generic iOS-blue, dark-navy sports clichés, and neon scoreboard looks.

### Out of scope (do not port)

- Membership / paywall screens
- SOS / crash / emergency
- Driving reports, speeding, phone-usage scores
- Fake iPhone bezels, Dynamic Island, fake status bars
- Item / pet / Tile trackers
- Battery percentages as a primary signal

### Definition of done

1. Launching the app lands on a full-bleed map of the current team.
2. Each player is a circular character pin with a white ring and a pointer.
3. A team pill at the top switches the whole map’s population.
4. A bottom sheet lists the same people, in sync with the pins.
5. Tapping a pin selects; tapping again (or tapping the row) opens player detail on a focused map.
6. Venues appear as geofence rings + a Places/Venues list.
7. Tokens, type, and status chips match this file.
8. Copy uses the vocabulary in §8. No leftover “Circle,” “Family,” “Check in,” or “Membership.”

---

## 1. Product feel

The job of the home screen is: **a captain opens the app and instantly sees where the squad is.**

There is no feed first. The map *is* the home screen. Atmosphere is “calm match-day control”: lavender sky, warm character colors, soft paper sheets, violet only for brand actions. Urgency is rare. Green means they made it to the pitch. Violet means they are still moving.

The spine of the product:

1. **Team map** — full-bleed, washed lavender streets, player pins.
2. **Team pill** — top, e.g. `Night Owls ▾`. Switching a team reloads who appears on the map.
3. **Squad sheet** — draggable. Name, role, place, status chip. Same people as the pins.

Venues (pitch, gym) are secondary. They exist so the map has somewhere to gather around, not as a directory product.

### The identity-color rule

Every player gets a **fixed color**. That color is used on:

- pin selection halo
- (optional) trail if you show movement
- detail header accent

Do not reuse a color inside the same team. Do not use brand violet (`#7c3aed`) as a player color — violet is the team/brand spine.

Parents of this idea: you find “the teal one” before you read “Nim.”

---

## 2. Color

### Brand (never a player color)

| Token | Hex | Use |
|---|---|---|
| Electric Violet | `#7C3AED` | Pills that are *on*, primary actions, geofence stroke |
| Deep Ink | `#281950` | Headlines, names, logo wordmark |
| Midnight Plum | `#191034` | Overlay scrim base, darkest surface |

### Canvas

| Token | Hex | Use |
|---|---|---|
| Iris Haze | `#F1F2F9` | App canvas behind the map |
| Lavender Mist | `#E7E6F4` | Hairlines, chip rest state, avatar fallbacks |
| Paper | `#FFFFFF` | Sheet, pills, cards |
| Map wash | `#EBE7F6` | Map container fallback |

Map tiles should be filtered toward this world, not left as raw Google/OSM daylight:

```css
.leaflet-tile-pane {
  filter: saturate(0.55) hue-rotate(240deg) brightness(1.08) contrast(0.9);
}
```

A watercolor sky illustration may sit at the **top 20–28%** of the map, faded out with a mask, opacity ~0.4, `pointer-events: none`. It must never hide pins. If pins collide with the wash, shorten the wash.

### Text

| Token | Hex | Use |
|---|---|---|
| Ink | `#281950` | Primary |
| Heather | `#5E537C` | Role, place, supporting copy |
| Overcast | `#676B89` | Chevrons, low emphasis |

### Player identity (cycle in join order)

| Slot | Hex |
|---|---|
| Fox / peach | `#E8A07A` |
| Teal | `#5BB8B0` |
| Mustard | `#E3B341` |
| Sage | `#7BA86A` |
| Coral | `#E8899A` |
| Sky | `#7EA7D6` |
| Lilac | `#A78BFA` — only if it still reads distinct from brand violet |

### Status (rationed)

| Status | Chip text | Text | Fill |
|---|---|---|---|
| `pitch` | On the pitch | `#34A06A` | `#E5F6EC` |
| `warm` | Warming up | `#2F9E88` | `#E4F6F2` |
| `route` | En route | `#7C3AED` | `#EFE7FF` |
| `gym` | At the gym | `#C47A3A` | `#F8EFE4` |

Do not invent a red status for “late” unless the product truly needs a missed-kickoff state. If you add it, use it only then.

---

## 3. Type

### Families

- **Display / titles:** `Fraunces` (opsz 9–144, weight 500–600), letter-spacing `-0.03em`. Fallback `Georgia, serif`.
- **UI / body:** `DM Sans` (400 / 600 / 700). Fallback `-apple-system, sans-serif`.
- Not user-switchable. One pairing everywhere.

Closest paid Fly.io analogs: Mackinac (serif) + Fricolage Grotesque (UI). Use the Google fonts above unless the sports app already has a license for those.

### Hierarchy

| Role | Face | Size | Weight | Notes |
|---|---|---|---|---|
| Screen title (`Squad`, `Venues`) | Fraunces | 30px | 500 | Sheet heading |
| Wordmark (`Rally` or product name) | Fraunces | 18px | 500 | Top-left mark |
| Team pill | Fraunces | 17px | 500 | Current team name |
| Player name | DM Sans | 17px | 700 | Always bold |
| Role · place | DM Sans | 13px | 600 | Heather |
| Status chip | DM Sans | 12px | 700 | Colored pill |
| Kickoff meta | DM Sans | 13px | 600 | `2 of 5 at the pitch · kickoff 7:00` |
| Filter chip | DM Sans | 14px | 700 | |
| Speed badge | DM Sans | 11px | 700 | On the pin, e.g. `12 km/h` |

Do not uppercase body copy. No condensed esports fonts. No numeric LED scoreboard type.

---

## 4. Layout & UX structure

### Home (the only first screen)

```
┌─────────────────────────────────┐
│  [Wordmark]   [ Team name ▾ ]   │  floating
│                                 │
│           MAP (full bleed)      │
│     pins + venue rings          │
│                                 │
│─────────────────────────────────│
│ grabber                         │
│ 2 of 5 at the pitch · kickoff   │
│ [ Squad ] [ Venues ]            │
│ Squad                           │
│  (avatar) Name                  │
│           Role · Place          │
│           [status chip]         │
└─────────────────────────────────┘
```

- Map is edge-to-edge, including under the top bar and sheet.
- Top bar sits below the safe area.
- Sheet sits above the home indicator; detents: **peek** (~240–252px, one player + filters) and **expanded** (~78% height).
- Grabber is 38×5px, `#E7E6F4`, centered.
- Filter chips do not replace tabs. There is **no bottom tab bar** on home unless the existing app already has one that cannot be removed. Prefer sheet filters over a 4-tab bar.

### Team switcher

Tapping the team pill opens a sheet: `Your teams`, one row per team, name + `N players`. Active row uses violet. Switching a team:

- Changes the map’s player set
- Auto-fits pins
- Resets selection to a sensible default (captain, or first player)

### Pin vs row

- Tap pin → select (halo + fly to ~zoom 15.2).
- Tap the **same** pin again, or tap the sheet row → push **player detail**.
- Map and sheet stay in lockstep: the selected pin is the person at the top of the mental model.

### Player detail

- Back button (round paper circle, violet icon).
- Centered name + role.
- Map focused on that player only (no other pins, no venue rings unless they are *at* that venue).
- Bottom paper card: large character, name (serif), place, freshness (`already there` / `2 min ago`), status chip.

### Venues

On the map: translucent violet circle, fill `rgba(124,58,237,0.10)`, stroke 2px `rgba(124,58,237,0.45)`, plus a small emoji pin (⚽ pitch, 🏋️ gym, 🏟️ stadium, ☕ meet).

In the sheet: heading `Venues`, rows with emoji avatar, venue name, one-line match context (`Kickoff 7:00 · 5-a-side`).

---

## 5. Components

### Player pin (atomic)

- 48px circular character image
- 3px solid `#FFFFFF` ring
- 10px white diamond pointer under the pin
- Soft shadow `0 8px 18px rgba(40, 25, 80, 0.20)`
- Selected: 4px halo in the player’s identity color
- If `status === 'route'` and speed is known, a paper speed badge to the right: `12 km/h`
- Do not label pins with text names. Color + character is the ID.

### Character art

Use original watercolor + ink-outline mascots, one per player (or a small reusable set mapped by role). Style notes:

- Pastel, friendly, storybook — not 3D renders, not photos, not team-logo clipart
- Jersey / kit / ball allowed
- Square crop, faces readable at 48px
- No third-party brand marks

If the sports app already has real player photos, **prefer photos in the pin** and keep the rest of this visual system. Characters are for when photos are missing or the product wants a mascot layer (youth teams, casual kickabouts).

### Team pill

- Height 40px, fully rounded, paper fill
- Serif team name, ink
- Small `▾` in Overcast
- Shadow `0 8px 20px rgba(40, 25, 80, 0.10)`

### Wordmark chip

- 40px tall, 14px horizontal padding, 14px radius
- Paper, serif, ink
- Product name only. Not a navigation control.

### Filter chip

- Rest: mist fill, ink text, 40px height, pill
- On: `#7C3AED` fill, white text
- Leading 18px icon (people / pitch)

### Squad row

- Height ≥ 62px, full-row tap
- 52px character avatar
- Name 17/700 ink
- `Role · Place` 13/600 heather
- Status chip under the meta line
- Hairline `#E7E6F4` between rows

### Sheet

- Paper, 28px top radius
- Shadow `0 -12px 40px rgba(40, 25, 80, 0.12)`
- Peek shows kickoff line + filters + heading + ~1 row
- Expanded scrolls the list; grabber still visible

### Overlay

- Scrim `rgba(25, 16, 52, 0.35)`
- Same sheet language as the squad sheet

---

## 6. Motion

- Pin select: map flies to the player in ~550ms.
- Sheet: expand/collapse 250ms ease. Drag 1:1 if you implement native detents; otherwise tap the grabber.
- Team switch: cross-fade pins ~200ms, then fit bounds with padding top 110 / bottom 280 so pins sit in the visible map between chrome.
- Pins never teleport on location update — ease along the path (~600ms) if live location exists.
- Do not bounce, do not use game-like screen shake.

---

## 7. Spacing & radius

- 4px base. Common: 8, 10, 12, 14, 18, 20, 28.
- Floating chrome inset from screen edges: 14px.
- Sheet padding: 8px 18px 20px, plus safe-area on the bottom.
- Radius: chips/pills 999; sheet 28; wordmark 14; avatars 50%; cards 28.

---

## 8. Copy & domain language

Replace locator-app words:

| Do not say | Say |
|---|---|
| Circle / Family | Team / Squad |
| Places | Venues |
| Check in | On the pitch (status), or drop it |
| Last seen | `already there`, `2 min ago`, `warming up` |
| People | Squad |
| Membership | (omit) |
| SOS | (omit) |

Kickoff line format:

`{n} of {total} at the pitch · kickoff {time}`

Status labels are fixed:

- On the pitch
- Warming up
- En route
- At the gym

Add sport-specific statuses only if the app has the data (e.g. `On the bench`, `Injured`). Keep the same chip pattern.

---

## 9. Screens the refactor must cover

1. **Squad map (home)** — map + team pill + sheet.
2. **Team picker** — sheet of teams.
3. **Venues** — filter on the same home sheet, plus geofences on the map.
4. **Player detail** — focused map + paper card.

Optional, only if the existing app already has them — restyle, don’t invent:

- Fixture / kickoff detail (can remain a sheet over the map)
- Chat (entry can be a round paper button, but not required)
- Settings (gear in a round paper button, ink/violet icon)

Do not add Driving, Safety, or Membership tabs.

---

## 10. Do / don’t

**Do**

- Open on the map.
- Give every player a fixed identity color.
- Use violet only for brand (team UI, selected chips, venue rings).
- Wash the map toward lavender so characters stay the brightest objects.
- Show status as a chip, not as a battery.
- Float paper chrome over the map with soft plum-tinted shadows.
- Keep titles in Fraunces and names in DM Sans bold.

**Don’t**

- Don’t open to a dashboard, leaderboard, or chat thread.
- Don’t use player photos *and* tiny jersey numbers as the only way to scan the map — the pin must read at a glance.
- Don’t put a 4-item tab bar under a map unless the existing IA forces it.
- Don’t use Fly.io’s logo, balloon-leader mascot, or copied illustrations.
- Don’t use red except for a true missed-match / injury emergency.
- Don’t flatten pins (they need the white ring + pointer + shadow).
- Don’t leave raw colorful Mapbox/Google tiles; they fight the characters.

---

## 11. Refactor checklist for the agent

Work in the sports app repo, not by copying this prototype’s file tree blindly.

1. Read existing home, team, player, and venue routes.
2. Add design tokens (CSS variables or theme object) from §2–§3.
3. Load `Fraunces` + `DM Sans`.
4. Turn the main authenticated landing route into the squad map shell.
5. Implement pin + sheet + team pill using **existing** player/team APIs.
6. Map current presence fields onto `pitch | warm | route | gym` (or a documented extension).
7. Restyle player profile as the detail pattern in §4.
8. Restyle venues as geofences + sheet list.
9. Delete or hide chrome that contradicts this spec (paywalls on home, SOS, generic tab bars).
10. Walk the flow in a real device viewport: launch → see squad → switch team → open a player → back → venues.
11. Confirm other routes that share these components (player profile, team switcher) still match.

### Existing-app field mapping (fill this in while refactoring)

| This spec | Likely existing field |
|---|---|
| Team | club / team / group |
| Player | user / athlete / member |
| `role` | position / number |
| `place` | geocoded label / venue name |
| `status` | presence / check-in / geofence event |
| `speed` | location speed, only if already collected |
| Venue | field / facility / gym |

If a field does not exist, do not fake live GPS. Use last known venue + status from the product’s actual source of truth.

---

## 12. Prompt you can paste

```text
Read DESIGN.md and refactor this sports app’s UI/UX to match it.

Home must be a full-bleed squad map with identity-colored character (or photo) pins, a serif team pill, and a draggable paper bottom sheet listing the same players. Visual language: iris haze, violet ink, Fraunces + DM Sans, watercolor-storybook tone inspired by Fly.io but with original sports art only.

Use our real teams, players, and venues. Map our presence data onto the status chips in DESIGN.md. Do not add SOS, membership, driving reports, or a fake phone frame. Keep existing auth and data fetching.

When you are done, walk launch → team switch → player detail → venues and fix anything that still looks like the old dashboard.
```

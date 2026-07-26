# Competitor verification: 3D / IK overlay vs 2D scores

Deep-dive against the plan todo: verify whether **Tennis AI 2.0**, **sevensix**, and **OffCourtz** ship anything like this project's premium path (monocular 3D lift → DTW vs pro → CCD IK on the **user's own** skeleton → overlay on original footage).

**Method:** Public product pages, App Store / Play listings, FAQs, and third-party store intelligence (Jul 2026). No device install was possible in this environment; conclusions are from explicit product claims and architecture signals (on-device vs cloud, overlay wording, app binary size).

**Verdict in one line:** None of the three advertise or describe true 3D regression lifting + IK-corrected own-skeleton compositing. Closest is OffCourtz's "how you should have performed" overlay language; Tennis AI and sevensix are 2D (or MediaPipe-style) pose tracking + scores + side-by-side / curve comparison.

---

## Comparison matrix

| Capability | This project (premium) | Tennis AI 2.0 | sevensix | OffCourtz |
|---|---|---|---|---|
| Guided / side-on recording | Yes (outline contract) | Yes (Axel camera guide) | Tripod / friend film | Side-angle recommended |
| Pose / body tracking | RTMPose → MotionBERT 3D | On-device body track @ 30 fps; pose skeleton overlay | Stickman overlay; body tracking box | Frame-by-frame body angles (cloud) |
| Monocular 3D lift (temporal regression) | MotionBERT | Not claimed | "3D map" wording only (third-party); no lift pipeline claimed | Not claimed |
| Temporal alignment vs pro (DTW) | Keyframe-anchored DTW | Metric ranges vs pros | Similarity score vs pro | Parameter ranges vs top players |
| IK correction on **user** bone lengths | CCD IK, flawed joints only | No — live verbal/metric correction + drills | No — text + pro curve | Overlay of ideal technique claimed; **not** described as IK / bone-length preserving |
| Output: corrected skeleton on **user's own** footage | OpenCV overlay + ffmpeg | Your tracked skeleton; **split-screen** with pro skeletons | Stickman + **pro swing-curve** overlay | Technique overlays that sometimes show ideal motion; FAQ admits placement quality is imperfect |
| Primary deliverable | Overlay video + grounded text | Score / 107 metrics / drills / Axel | Score 1–100 + graphs + AI chat | 20+ param scores + 900+ exercises |

---

## Tennis AI 2.0 ([tennisai.net](https://tennisai.net/))

### What they ship (evidence)

- **On-device real-time analysis.** App Store release notes (v2.0 / 2.11): analysis runs on device, "No uploads, no internet needed on court." Binary ~**296 MB** — consistent with bundling on-device CV models.
- **Pose overlay of the user's tracked skeleton**, phase breakdown (preparation → follow-through), score /100, **107 biomechanical metrics** compared to professional **ranges**.
- **Pro comparison = side-by-side / split-screen** with pro players (site: "Compare your skeleton overlay side-by-side with professional players like Sinner and Alcaraz"), not an IK-adjusted copy of the user's body.
- **Live Correction mode:** Axel watches reps and confirms metric fixes verbally / via drills — coaching loop, not rendered corrected motion on the original clip.
- Earlier Play copy referenced MediaPipe-style 33-point tracking; current listings say "track your body in real time at 30 frames per second" without naming the stack. Architecture matches lightweight on-device pose (BlazePose / MediaPipe class), **not** server-side MotionBERT + IK.

### Traction / sentiment (re-checked)

| Signal | Value |
|---|---|
| Claimed active users | 5,000+ (site) |
| Google Play | 5K+ downloads, **1.8★ / 34 reviews** — signup failures, broken analysis |
| App Store | **3.0★ / 3 ratings** (US listing sparse) |
| Pricing | Free trial; Premium ~$9.99/mo or ~$99.99/yr |

### Conclusion vs this project

**Highest UX overlap** with Phase 1 + live coaching, but **not** the premium 3D IK overlay. Differentiation remains: they show *your detected pose* and *pro side-by-side*; you aim to show *your body corrected toward pro angles on your own footage*.

---

## sevensix ([sevensixtennis.com](https://sevensixtennis.com/))

### What they ship (evidence)

- Record swing on **iPhone only** → computer vision analyzes swing path, kinetic chain timing, ball impact point; score vs professional similarity.
- **Stickman overlay** (App Store "What's New" historically) for body movement / joint angles.
- **Pro curve overlay** — user's swing path vs ideal/pro curve (store intelligence / screenshots describe "pro curve" comparison), not a full corrected body skeleton on film.
- Third-party MWM listing mentions "3D map and complex graphs"; **no primary SevenSix doc** describes monocular 3D lifting, DTW alignment, or IK. Treat "3D map" as UI visualization of deviations, not MotionBERT-class reconstruction.
- App size ~**74–77 MB**; cloud analysis of videos is implied by "stuck analyzing" user complaints historically.

### Traction / sentiment (re-checked)

| Signal | Value |
|---|---|
| App Store | **~4.2–4.3★ / ~60–68 ratings** |
| Downloads (MWM estimate) | **25k+** (third-party; treat as approximate) |
| Pricing | Monthly ~$14.99; yearly ~$149.99; à-la-carte swing packs |
| Sentiment | Concept praised; recurring complaints: stuck analysis, camera glitches, dubious auto-scores |
| Platforms | **iOS only** (users asking for Android on community feed) |

### Conclusion vs this project

Strong overlap on **pro-compared technique scoring + visual swing feedback**. Still **2D / curve / stickman** coaching — **no** evidence of IK-corrected own-skeleton video.

---

## OffCourtz ([offcourtz.com](https://www.offcourtz.com/))

### What they ship (evidence)

- Upload or in-app record → cloud AI scores **20+ technique parameters** (hip rotation, knee bend, contact point, etc.) against biomechanical ranges of top players; total score = average of parameter scores ([FAQ](https://offcourtz.com/faq)).
- Matched drills from **900+** exercise library; 7 shot types.
- App binary ~**48 MB** → heavy analysis almost certainly **server-side**, not on-device 3D lifter.
- **Closest overlay claim of the three.** FAQ *"Why does the overlay not always look perfect?"*:

  > …in case the player can improve a technical parameter, the AI needs to show the player how they should have performed. Sometimes the AI doesn't depict this as it should…

  That is an intentional **ideal-technique visual** on the user's video — conceptually nearer to your Phase 3 goal than Tennis AI's side-by-side or sevensix's pro curve. It does **not** claim: 3D lift, bone-length-preserving IK, phase-anchored DTW, or easing flawed joints only.

### Traction / sentiment (re-checked)

| Signal | Value |
|---|---|
| App Store | **Not enough ratings** for a public average |
| Pricing | €9.99/mo or €99.99/yr; 3 free analyses |
| Sentiment | Website testimonials only; no large independent review corpus |
| Platforms | App Store + Google Play |

### Conclusion vs this project

**Closest product language** to "show the corrected motion on my clip," but implementation reads as **2D parameter scoring + imperfect graphic overlays**, not the full 3D → DTW → CCD IK pipeline. Their FAQ admitting bad overlay placement is also a trust risk you should avoid by validating deltas before shipping overlays (matches your Phase 2 → Phase 3 order).

---

## Implications for Spolysis

1. **Premium moat still open.** Public competitors sell scores, drills, chat coaches, stickmen, pro curves, and side-by-side skeletons. None document MotionBERT-style lift + CCD IK on the user's proportions.
2. **Watch OffCourtz overlays** as the nearest narrative competitor; if they harden "how you should have moved" visuals, message differentiation must stress *your skeleton, your bone lengths, only flawed joints, eased blend*.
3. **Do not race Tennis AI on live on-device MediaPipe coaching** as the core bet — they already occupy that lane (with poor store reliability). Win on **offline quality-gated server pipeline + trustworthy correction video**.
4. **Reliability is the shared failure mode** of form apps (Tennis AI 1.8★ Android; sevensix analysis stuck; OffCourtz overlay FAQ). Your quality gate + professor-validated deltas before render is the right counter-strategy.

---

## Sources

- [Tennis AI 2.0 site](https://tennisai.net/), [App Store](https://apps.apple.com/us/app/tennis-ai-2-0/id6738391148), [Google Play](https://play.google.com/store/apps/details?id=com.tennis.ai)
- [sevensix App Store](https://apps.apple.com/us/app/sevensix-tennis-ai-coach/id1505604446), [About](https://sevensixtennis.com/spaces/cly8klol60001g2lor0vcu6kr), [MWM store intel](https://mwm.ai/apps/sevensix-tennis-ai-coach/1505604446)
- [OffCourtz site](https://www.offcourtz.com/), [FAQ (score + overlay)](https://offcourtz.com/faq), [App Store](https://apps.apple.com/us/app/offcourtz-ai-tennis-training/id6456525563)

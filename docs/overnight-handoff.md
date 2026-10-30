# Overnight handoff

## Current phase

Iteration 4 implements truthful missing-video and storage-outage recovery.
Native validation, screenshot review, Python/static checks, and process cleanup are complete for this batch.
Work stays in `overnight/prepared`; no worker commits, pushes, deployment, production mutations, or additional agents.
GNHF owns `notes.md`; checkpoint status goes in ignored iteration sidecars.

## Completed work

- Phase 1: completed-result retry, refreshed signed-link recovery for video and motion, bounded and cancellable motion download, and repaired native test interactions.
- Phase 2: progress routes identify each job or clip, result routes identify each job, and offscreen completion waits for focus before navigating.
- Pending jobs reopened from history can retry confirmation using the existing ownership-checked endpoint without uploading again.
- Confirmation failure explains that the video transfer finished and offers Start analysis again.
- Progress content scrolls when vertical space is limited.
- Background history polls no longer activate the native pull-to-refresh animation; manual refresh keeps its own loading state.
- Native tests cover distinct-job navigation, rejection guidance, pending-job restart, and confirmation retry with transfer counters.
- Recovery test setup resets fixture state before every test, because assertion aborts can bypass Swift defer cleanup.
- Sign-in waits for the delayed native password-save prompt before opening history.
- Phase 3: loaded history remains visible with a stale-status warning and retry when refresh fails; unavailable initial history no longer claims zero analyses.
- Failed pagination stops automatic requests after the normal retry budget and offers explicit retry for older analyses.
- Native history checks cover initial outage, a genuinely empty account, failed processing-job polling, and second-page recovery with bounded request counts.
- Phase 4: missing or invalid saved uploads clear the local upload-success assumption and retry the actual transfer when the selected clip remains available.
- History-only pending jobs direct the athlete to select the original video again after validation fails; pending jobs no longer show a reconstruction spinner before start.
- Storage service, permission, and connectivity failures return retryable 503 rather than claiming the athlete's video is invalid; ownership and the existing 400 validation contract remain intact.
- Native transfer-failure and missing-video checks assert transfer and confirmation counts plus recovered video readiness; nine new HTTP integration cases bring the Python suite to 24 passing tests.
- Signed-in tests reset the fixture independently so a failed recovery assertion cannot leak a simulated outage into the next journey.

## Native setup

The installed `com.spolysis.app` is a compatible development shell without an embedded JavaScript bundle.
Use Metro from this checkout; no native rebuild was required.
Simulator: iPhone 17 Pro, iOS 26.5, UDID `858FB450-9823-4060-AADB-CDB3CBB58445`.
The system Ruby has `xcodeproj` 1.28.1; CocoaPods is unnecessary for this installed shell.
Every command below runs from the repository root.

```sh
xcrun simctl boot 858FB450-9823-4060-AADB-CDB3CBB58445
xcrun simctl bootstatus 858FB450-9823-4060-AADB-CDB3CBB58445 -b
ruby app/e2e/create-project.rb /tmp/SpolysisOvernightUITests.xcodeproj
```

Start the fixture and Metro in separate terminals:

```sh
.venv-test/bin/python app/e2e/fixture.py --media-dir .gnhf/media --result .gnhf/media/result.json
```

```sh
EXPO_PUBLIC_SUPABASE_URL=http://localhost:8877 EXPO_PUBLIC_SUPABASE_ANON_KEY=fixture-anon EXPO_PUBLIC_API_URL=http://localhost:8877 npm --prefix app start -- --clear --port 8081
```

Actual pipeline media is in ignored `.gnhf/media/overlay.mp4`, `.gnhf/media/skeleton.json`, and `.gnhf/media/result.json`.
Phase 1 downloaded it read-only from `results/34406f21-3fa4-425e-918f-7f7efad187e3/` using main-checkout ignored configuration in memory.
No credentials were copied into this worktree or printed.
The simulator library already contains the overlay used for import; it exercises transfer behavior, not reconstruction accuracy on raw footage.
If the library is reset, use `xcrun simctl addmedia 858FB450-9823-4060-AADB-CDB3CBB58445 .gnhf/media/overlay.mp4`.
Fixture credentials must never enter a distribution build.

## Phase 4 verification

The first native bundle reproduces missing-video start-only retry from history.
Its import test did not leave history after a tab tap, so the corrected import baseline uses the established result-to-capture path.
That baseline reproduces a successful-upload claim even after confirmation rejects the stored video.
Bundles: `/tmp/spolysis-overnight-phase4-before.xcresult` and `/tmp/spolysis-overnight-phase4-transfer-before.xcresult`.
Exported baseline attachments: `.gnhf/evidence/phase4-before` and `.gnhf/evidence/phase4-transfer-before`.

```sh
xcodebuild clean test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase4-verified.xcresult CODE_SIGNING_ALLOWED=NO
```

Consolidated result: all 14 tests pass with zero failures in 287.153 seconds.
This covers all 12 recovery tests, the signed-in journey with import/viewer/share/sign-out, and authentication screens.
Log: `/tmp/spolysis-overnight-phase4-verified.log`.
The first consolidated attempt, `/tmp/spolysis-overnight-phase4-final.xcresult`, passed 11 of 14 tests.
A dropped history tap made no detail request, the confirmation outage leaked into the following signed-in test, and the resulting missing sign-out blocked the authentication smoke.
Signed-in setup now resets the fixture independently, and confirmation import uses the shared result-to-capture helper.
History entry uses explicit visible-center coordinates without automatic tap retries.
The failed tap's recorded coordinates were already centered, so its root cause is not established; do not attribute every dropped simulator tap to polling.
The fresh consolidated pass did not repeat it.
Keep app-directory files unchanged during native validation to avoid Metro refresh interference.

The first recovered screenshots captured the result transition before proving video readiness.
After the consolidated pass, only the two transfer tests gained a native video-ready assertion; product code remained unchanged.
Both strengthened checks pass with zero failures in 67.183 seconds using this command:

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests/ResultRecoveryTests/testInvalidUploadedVideoRetriesTransfer -only-testing:SpolysisUITests/ResultRecoveryTests/testInterruptedTransferRetriesBeforeStartingAnalysis -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase4-playback.xcresult CODE_SIGNING_ALLOWED=NO
```

Affected-flow log: `/tmp/spolysis-overnight-phase4-playback.log`.
Final failure-state attachments are `.gnhf/evidence/phase4-verified`; strengthened playback captures are `.gnhf/evidence/phase4-playback`.
The five new failure and recovered states were visually inspected at 1206 x 2622.
Three failure screenshots are preserved under `docs/screenshots`.
The first consolidated attachments are `.gnhf/evidence/phase4-first-pass`.
The consolidated journey ends signed out; the later affected playback checks sign back into the isolated fixture and end on a result before termination.
Fixture and Metro logs: `/tmp/spolysis-overnight-phase4-fixture.log` and `/tmp/spolysis-overnight-phase4-metro.log`.
TypeScript, ESLint, viewer build during Metro startup, Ruff, and changed Python-file formatting pass.
Phase 4 static and CPU commands:

```sh
npm --prefix app run typecheck
npm --prefix app run lint
.venv-test/bin/python -m pytest -q
.venv-test/bin/python -m ruff check api pipeline tests app/e2e/fixture.py
.venv-test/bin/python -m ruff format --check api/r2.py api/routers/uploads.py tests/test_api_flow.py app/e2e/fixture.py
app/node_modules/.bin/prettier --check app/src/screens/UploadProgressScreen.tsx app/src/services/api.ts
git diff --check
```

The full Python suite passes all 24 tests in 8.11 seconds with two dependency deprecation warnings.
Those warnings concern Starlette's httpx test adapter and the existing Supabase gotrue package.
API/storage integration tests verify absent objects, invalid size/type, service and permission errors, connection failure, and start-only retry using the same pending job.
The fixture-native checks and HTTP integration tests are separate validation layers, not a production full-stack claim.
The API's storage error classification requires deployment before or alongside the app change, since the old API can also return 400 for a storage outage.
No deployment was performed.
HTTP transfer failures do not establish device airplane-mode or process-termination recovery.

## Earlier verification and evidence

Phase 3 uses the consolidated command below, with its own result bundle and log.
The fixture now supports real 20-row pagination and independent history and page-failure switches.
The initial pagination baseline reproduces repeated failed-page requests and no retry control.
Its first refresh test did not initiate a request, so the corrected refresh baseline uses the existing five-second processing-job poll.
That baseline verifies failed history responses and no stale-data warning.
The baseline bundles are `/tmp/spolysis-overnight-phase3-before.xcresult` and `/tmp/spolysis-overnight-phase3-refresh-before.xcresult`.
Their exported attachments are `.gnhf/evidence/phase3-before` and `.gnhf/evidence/phase3-refresh-before`.

```sh
xcodebuild clean test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase3-final.xcresult CODE_SIGNING_ALLOWED=NO
```

Final native result: all 11 tests pass with zero failures in 210.171 seconds.
This is one uninterrupted consolidated pass on the final product and native-test source.
All nine recovery tests, the signed-in imported-video journey with sign-out, and the authentication screens pass.
The new pagination assertion records three failed requests, then one successful explicit retry; the final older row becomes accessible.
All six new history screenshots were inspected at 1206 x 2622.
The three failure-state screenshots are preserved under `docs/screenshots/history-*.png`; all recovered states are in `.gnhf/evidence/phase3-final`.
The final journey ends signed out on the sign-in screen.
Log: `/tmp/spolysis-overnight-phase3-final.log`.
Fixture and Metro logs: `/tmp/spolysis-overnight-phase3-fixture.log` and `/tmp/spolysis-overnight-phase3-metro.log`.
TypeScript, ESLint, Prettier for HomeScreen, Python lint, fixture formatting, and diff whitespace checks pass.
The viewer build passed during Metro startup.
No API or pipeline implementation changed; the Python regression suite was not repeated.
Service outages use isolated HTTP 503 responses, not device airplane mode or production services.

### Earlier verification

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase2-verified.xcresult CODE_SIGNING_ALLOWED=NO
```

Use a new result-bundle path on each run.
The consolidated pass before the final history-refresh change passed seven of eight tests; the affected flows passed after repair as recorded below.
Its log is `/tmp/spolysis-overnight-phase2-verified.log` and fixture log is `/tmp/spolysis-overnight-phase2-fixture.log`.
The first consolidated attempt, `/tmp/spolysis-overnight-phase2-final.xcresult`, passed seven of eight tests.
Its completed-result check used leftover jobs from a failed baseline; per-test fixture reset fixes that setup failure.
The next consolidated pass, `/tmp/spolysis-overnight-phase2-verified.xcresult`, passed seven of eight tests in 183.346 seconds.
The pending test's history tap coincided with a background poll, made no detail request, and left the history visible.
The app had been activating the native refresh control for all background refetches.
Only manual refresh now activates it.
Affected history flows run twice with this command:

```sh
xcodebuild test -project /tmp/SpolysisOvernightUITests.xcodeproj -scheme SpolysisUITests -only-testing:SpolysisUITests/ResultRecoveryTests/testPendingUploadCanResumeFromHistory -only-testing:SpolysisUITests/ResultRecoveryTests/testSwitchingPendingAnalysesShowsSelectedJob -only-testing:SpolysisUITests/SignedInTests -test-iterations 2 -destination 'platform=iOS Simulator,id=858FB450-9823-4060-AADB-CDB3CBB58445' -derivedDataPath /tmp/spolysis-overnight-ui -resultBundlePath /tmp/spolysis-overnight-phase2-history-verified.xcresult CODE_SIGNING_ALLOWED=NO
```

Affected-flow result: six executions, zero failures in 165.658 seconds.
Pending-job recovery, distinct-job selection, and the full signed-in journey each passed twice after the final history-refresh fix.
The phase 2 full-suite run also passed completed-result recovery, video recovery, motion and signed-link recovery, confirmation retry, and authentication smoke before that Home-only change.
The confirmation test recorded one upload and two start attempts; the pending-history test recorded no upload and one start attempt.
Phase 2 did not produce one uninterrupted eight-test pass on that iteration's final source; the phase 3 consolidated pass now covers those flows together.
Final affected-flow attachments are `.gnhf/evidence/phase2-history-verified`.
The pending and rejected screenshots under `docs/screenshots` come from the final repeated pass.
The confirmation screenshot comes from the earlier successful confirmation flow; its progress-screen implementation is unchanged.
Its log is `/tmp/spolysis-overnight-phase2-history-verified.log`.
Native baseline bundles are `/tmp/spolysis-overnight-phase2-before.xcresult` and `/tmp/spolysis-overnight-phase2-history-before.xcresult`.
The first switching baseline hit the delayed password-save dialog; the signed-in rerun reproduced the actual wrong-job defect.
Baseline attachments are under `.gnhf/evidence/phase2-before` and `.gnhf/evidence/phase2-history-before`.
The first consolidated attachments are under `.gnhf/evidence/phase2-final`.

Phase 1 passed five native tests with zero failures in 115.025 seconds.
Its bundle is `/tmp/spolysis-overnight-phase1-final.xcresult`, log is `/tmp/spolysis-overnight-phase1-final.log`, and attachments are `.gnhf/evidence/phase1-final`.
Together these journeys exercise isolated authentication, history, real pipeline overlay and motion playback, 3D controls, stroke/hand selection, library import, native upload, sharing, profile, sign-out, and recovery.
Production authentication and database writes are separate unverified claims.

The following static checks pass in phase 3:

```sh
npm --prefix app run typecheck
npm --prefix app run lint
npm --prefix app run build:viewer
.venv-test/bin/python -m ruff check api pipeline tests app/e2e/fixture.py
.venv-test/bin/python -m ruff format --check app/e2e/fixture.py
app/node_modules/.bin/prettier --check app/src/screens/HomeScreen.tsx
git diff --check
```

The viewer build ran during Metro startup.
No API or pipeline implementation changed, so the Python regression suite was not repeated in either phase.

## Remaining ranked work and deferred decisions

1. Actual network interruption, failed jobs, recording guidance, and app termination during transfer.
   HTTP transfer-failure and missing-upload recovery are implemented in phase 4.
2. Session expiry/recovery, privacy expectations, account boundaries, and actual device-offline behavior across screens.
   History service-failure and pagination recovery are implemented in phase 3.
3. Actionable coaching and comparison interpretation, including the mismatch between highlighted joint and coaching priority in the inspected volley result.
4. Dynamic Type, smaller screens, accessibility, and remaining empty/loading/error states.
5. Consolidated native validation and honest handoff after those phases.

See [Athlete review](athlete-review.md) for issue evidence and claim limits.
Production Supabase DNS was unavailable when checked on 2026-10-30 in phase 1.
Physical camera behavior, Android runtime, distribution signing, external account access, and model accuracy remain separate requirements.

Durable upload queues and abandoned-job cleanup require a coordinated lifecycle and retention decision.
A transfer retry currently creates a new pending job through the existing upload contract, so failed or abandoned pending rows may remain.
This phase repairs recovery without adding a renewal endpoint, changing the data model, or silently defining retention.
Recommendation for morning review: define explicit uploading, ready-to-start, and abandoned states with authenticated retry and retention before adding background transfers.
Phase 2 recovers confirmation using the existing contract and does not implement that larger change.

## Checkpoint and cleanup

Phase 1 checkpoint: `.gnhf/checkpoints/iteration-1-result-recovery.patch`.
Phase 2 checkpoint: `.gnhf/checkpoints/iteration-2-upload-recovery.patch`.
Phase 3 checkpoint: `.gnhf/checkpoints/iteration-3-history-recovery.patch`.
Phase 4 checkpoint: `.gnhf/checkpoints/iteration-4-upload-validation.patch`.
Each has an ignored status sidecar in `.gnhf/runs/objective-act-as-a-d-19111c/`.
Phase 4 Metro on 8081 and the fixture on 8877 are stopped; neither port has a listening process.
The test app was terminated and this worker-booted simulator was shut down, preserving its installation and data.
The consolidated journey ends signed out; the final affected playback checks use a local fixture session and end on a result before termination.
All worker-started long-running processes are stopped.
No useful-work exhaustion or production-release claim is made; continue the ranked backlog next iteration.

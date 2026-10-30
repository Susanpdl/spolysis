# Native UI checks

These tests drive the installed iOS app through XCTest.
`SmokeTests` checks the welcome, sign-up, and sign-in screens.
`SignedInTests` uses an isolated local HTTP fixture and actual pipeline media to exercise history, result playback, the 3D viewer, recording setup, library import, native upload, file sharing, and sign-out.
`ResultRecoveryTests` checks completed-result download failures, video failures, motion failures, and a failed signed-link refresh followed by successful recovery.
Fixture authentication is not production authentication and never enters the app source.

## Prepare the test project

Build and install the native simulator app first.
The project generator uses the `xcodeproj` Ruby gem, which may already be installed or distributed with CocoaPods.

```sh
ruby app/e2e/create-project.rb
```

If Ruby cannot load `xcodeproj`, locate the installed CocoaPods gem directory and set `GEM_HOME` for this command.
Do not assume a previous Homebrew installation path still exists.
The installed compatible native development shell can be reused with Metro serving this checkout.
An app without an embedded JavaScript bundle needs Metro running before launch.

## Authentication screens

Start Metro with normal application configuration, then run the test against a simulator without an existing session:

```sh
xcodebuild clean test \
  -project /tmp/SpolysisUITests.xcodeproj \
  -scheme SpolysisUITests \
  -only-testing:SpolysisUITests/SmokeTests \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath /tmp/spolysis-ui-build \
  CODE_SIGNING_ALLOWED=NO
```

## Signed-in result flow

Download a completed pipeline result's overlay to `overlay.mp4` and skeleton to `skeleton.json` in a temporary media directory.
Keep its result metadata in a separate JSON file.
The fixture substitutes local media URLs into that metadata.
Add a short tennis video to the simulator's photo library before running the import test.
Use a dedicated simulator library with that video as its first video asset.
The test selects its thumbnail by accessibility label and taps its center because Photos does not expose a usable accessibility hit point for the image.
Navigation uses ordinary XCTest taps; 150 ms long presses were dropped on the current iOS 26.5 simulator.
The history interaction waits for its row to become hittable before tapping.
The fresh-install flow dismisses iOS's password-save dialog and grants the test app photo-library access through the native permission dialog.

```sh
python3 app/e2e/fixture.py --media-dir /tmp/spolysis-e2e-media --result /tmp/spolysis-thetis-result.json
```

In a separate terminal:

```sh
cd app
EXPO_PUBLIC_SUPABASE_URL=http://localhost:8877 \
EXPO_PUBLIC_SUPABASE_ANON_KEY=fixture-anon \
EXPO_PUBLIC_API_URL=http://localhost:8877 \
npm start -- --clear
```

Run the same XCTest command with `-only-testing:SpolysisUITests/SignedInTests`.
Run `-only-testing:SpolysisUITests/ResultRecoveryTests` for the failure and recovery checks.
These checks toggle outages through the loopback fixture's `/__test/failures` endpoint and restore them after each test.
Use `-only-testing:SpolysisUITests` for a consolidated pass: recovery tests, the signed-in journey with sign-out, then the authentication screens.
Use a fresh result bundle path when saving screenshots and test evidence.
A clean test build avoids stale XCTest discovery after test source changes.
Stop the fixture and restart Metro with normal configuration afterward.
Never distribute a build configured for this fixture.

The native camera needs a physical device.
Simulator video import and result review do not validate camera orientation, focus, or framing performance on a real phone.

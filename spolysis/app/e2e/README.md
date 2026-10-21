# Native UI checks

These tests drive the installed iOS app through XCTest.
`SmokeTests` checks the welcome, sign-up, and sign-in screens.
`SignedInTests` uses an isolated local HTTP fixture and actual pipeline media to exercise history, result playback, the 3D viewer, recording setup, library import, native upload, file sharing, and sign-out.
Fixture authentication is not production authentication and never enters the app source.

## Prepare the test project

Build and install the native simulator app first.
The project generator uses the `xcodeproj` Ruby gem distributed with CocoaPods.

```sh
GEM_HOME="$(brew --prefix cocoapods)/libexec" ruby app/e2e/create-project.rb
```

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
The first history interaction uses a 150 ms press to avoid dropped instantaneous XCTest taps during debug startup.
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
Use a fresh result bundle path when saving screenshots and test evidence.
A clean test build avoids stale XCTest discovery after test source changes.
Stop the fixture and restart Metro with normal configuration afterward.
Never distribute a build configured for this fixture.

The native camera needs a physical device.
Simulator video import and result review do not validate camera orientation, focus, or framing performance on a real phone.

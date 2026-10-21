# Simulator workflow recording

`spolysis-workflow-demo.mp4` is a 2-minute, 9-second H.264 video (720 x 1654, 30 fps, approximately 3.3 MB) that records the app running in an isolated iPhone simulator.
The edited walkthrough removes simulator startup, retries, and idle time.
It shows the account screens, demo sign-in, stroke and handedness selection, video import, corrected video, interactive 3D playback, sharing, analysis history, and sign-out.

The recording uses the local UI test service for authentication, upload, and job completion.
The corrected video and skeleton are real artifacts from a previously completed GPU analysis of the sample tennis clip.
Selecting a clip in this demo does not start a new GPU analysis.
The visible video label identifies these limitations.
Live camera recording requires a physical phone and is not included.

The production Supabase database was reachable on October 20, 2026.
The latest production upload was still pending, and Fly had no dedicated analysis worker running.
This recording demonstrates the interface, not a completed production end-to-end analysis.

During recording, a horizontal drag in the 3D viewer could trigger native back navigation.
The result screen now disables the competing native back gesture.
An automated simulator check passed rotation, reset, sharing, history, and sign-out after this change.
Type checking and lint also passed.
The existing result-flow UI test now includes the rotation regression check.
Previously distributed standalone builds do not include this source change yet.

The exported MP4 was decoded completely without errors and its major screens were visually reviewed.

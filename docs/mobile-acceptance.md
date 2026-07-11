# Mobile and PWA Acceptance Checklist

Run this checklist on at least one Android or iPhone before a release. Use a temporary test question where possible.

## Installation and startup

- Open `/app` over HTTPS or localhost and confirm all Chinese labels render correctly.
- Install the PWA and confirm the name is `WrongBook` with the Chinese wrong-question organizer suffix.
- Launch from the home-screen icon and confirm it opens in standalone mode.
- Refresh once after deployment so the updated Service Worker cache is activated.

## Capture and upload

- Tap the image picker and confirm the rear camera is offered where supported.
- Photograph a portrait question and upload it once.
- Confirm the upload button disables while the request is running.
- Repeat with a large image and confirm a clear error appears if it exceeds 20 MiB.
- Disable the network during an upload and confirm the page reports failure without creating a false success state.

## OCR and correction

- Start the Windows OCR Worker and confirm a pending job becomes succeeded or failed.
- Restart the Worker while a job is pending and confirm polling resumes.
- Open the recognized question and verify the image, OCR text, correction fields, tags, and knowledge points remain usable in portrait orientation.
- Save a correction and reload the page to confirm it persists.

## Review and library

- Schedule a review, complete it from Today Review, and confirm the next due date changes.
- Check review history filters and both pagination controls.
- Check question search, status filtering, archive, and restore.
- Export filtered JSON, import it as new questions, and confirm old IDs, images, OCR jobs, and review history are not copied.

## Layout and accessibility

- Test at approximately 390 CSS pixels wide and confirm there is no horizontal scrolling.
- Confirm the refresh button, upload controls, statistics cards, and pagination buttons remain fully visible.
- Navigate with an external keyboard: `/` focuses search, `R` refreshes, and `Ctrl/Cmd+S` saves an open question.
- Enable larger system text and confirm controls remain operable.

## Data safety

- Run a verified backup before deployment.
- Restore the backup into a temporary directory and confirm the database and uploaded images are readable.
- Confirm databases, uploads, backups, logs, and OCR models remain outside Git.

## Recorded phone feedback

- Some phone browsers open the camera-only capture flow and do not offer the photo gallery from the current picker. Keep this as a future upload UI task with separate Camera and Gallery controls.
- The current single-page dashboard should later be redesigned as a directory-style mobile app with bottom navigation. This redesign is intentionally deferred until the OCR workflow is stable.

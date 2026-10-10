# Navigation

Expo Router reads `app/`: the stack in `app/_layout.tsx`, the trail list at `/` and one
trail at `/trail/[id]`. Each route renders a page from `src/pages/` and nothing else.

`features/start-hike` starts the timer and asks the `trail-haptics` module for a pulse.
The module's TypeScript calls `requireNativeModule('TrailHaptics')`; the Swift class under
`ios/` and the Kotlin class under `android/` register under that name.

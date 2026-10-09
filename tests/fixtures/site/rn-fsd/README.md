# Moss Trail

A hiking companion for iOS, Android and the web: pick a trail, start a hike, feel a pulse at
every waypoint. Built with Expo and React Native in the Feature-Sliced layout; the
[navigation notes](docs/navigation.md) explain how the routes reach the slices.

`app/` holds Expo Router's routes, each a thin file over a page under `src/pages/`.
`modules/trail-haptics/` is a local Expo module with a Swift and a Kotlin side.
`src/screens/` is from before the move to Feature-Sliced Design.

# Tidewater

Tidewater serves a catalogue of harbour berths over HTTP.

![How a request flows](docs/images/flow.png)

## Deploying

The Helm chart under `deploy/` reads the image tag from {{ .Values.image.tag }}; set
`{{ .Values.replicaCount }}` for the number of pods. The [operations notes](docs/operations.md)
cover the rest, and the licence is in [LICENSE](LICENSE).

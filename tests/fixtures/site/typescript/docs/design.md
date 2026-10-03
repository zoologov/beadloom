# Design

`notes` holds the notes: `api` answers requests, `store` keeps notes and `model` holds the
rules for one note. `accounts` knows who is asking: `session` reads a token and `users` holds
the people. The API reads through `store` and checks the caller through `session`.

`reports` builds the weekly digest. It still reads the note store directly; the team moves it
onto the API and keeps the direct read flagged until then.

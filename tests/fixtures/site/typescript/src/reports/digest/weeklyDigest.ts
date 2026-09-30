import type { NoteStore } from "../../notes/store/noteStore.js";

export function weeklyDigest(store: NoteStore, author: string): string {
  const notes = store.byAuthor(author);
  const lines = notes.map((note) => `- ${note.title}`);
  return [`${author}: ${notes.length} notes`, ...lines].join("\n");
}

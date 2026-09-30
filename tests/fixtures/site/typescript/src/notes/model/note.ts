import { TITLE_LIMIT } from "../store/limits.js";

export interface Note {
  id: number;
  author: string;
  title: string;
  body: string;
}

export function makeNote(id: number, author: string, title: string, body: string): Note {
  const trimmed = title.trim();
  if (trimmed === "" || trimmed.length > TITLE_LIMIT) {
    throw new Error(`a note needs a title of 1 to ${TITLE_LIMIT} characters`);
  }
  return { id, author, title: trimmed, body };
}

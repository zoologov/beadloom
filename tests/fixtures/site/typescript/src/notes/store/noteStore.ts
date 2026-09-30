import { makeNote, type Note } from "../model/note.js";

export class NoteStore {
  private readonly notes: Note[] = [];

  add(author: string, title: string, body: string): Note {
    const note = makeNote(this.notes.length + 1, author, title, body);
    this.notes.push(note);
    return note;
  }

  byAuthor(author: string): readonly Note[] {
    return this.notes.filter((note) => note.author === author);
  }
}

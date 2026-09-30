import { createServer, type Server } from "node:http";
import { callerOf } from "../../accounts/session/session.js";
import type { Note } from "../model/note.js";
import { NoteStore } from "../store/noteStore.js";

export function titles(notes: readonly Note[]): string[] {
  return notes.map((note) => note.title);
}

export function startServer(store: NoteStore, port: number): Server {
  const server = createServer((request, response) => {
    const caller = callerOf(request.headers.authorization ?? "");
    response.setHeader("content-type", "application/json");
    if (caller === null) {
      response.statusCode = 401;
      response.end("[]");
      return;
    }
    response.end(JSON.stringify(titles(store.byAuthor(caller.name))));
  });
  return server.listen(port);
}

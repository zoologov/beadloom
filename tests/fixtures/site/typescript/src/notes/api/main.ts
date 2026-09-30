import { NoteStore } from "../store/noteStore.js";
import { startServer } from "./server.js";

startServer(new NoteStore(), Number(process.env.PORT ?? 8080));

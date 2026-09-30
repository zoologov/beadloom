// beadloom:component=site-shared
// A word quoted for a POSIX shell, so a command pasted into a terminal names what it shows.

/** The characters a shell reads as themselves in an unquoted word. */
const PLAIN_WORD = /^[A-Za-z0-9_\-./:@%+=,]+$/;

/**
 * `word` as the shell reads it back whole: unchanged when every character is
 * plain, otherwise in single quotes, with each `'` closed, escaped and reopened.
 */
export function shellQuote(word) {
  const text = String(word ?? "");
  if (PLAIN_WORD.test(text)) return text;
  return `'${text.replace(/'/g, "'\\''")}'`;
}

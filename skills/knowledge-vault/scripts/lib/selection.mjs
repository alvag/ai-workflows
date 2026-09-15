/**
 * Selects the documents that form an SDD flow's verified vault frontier.
 *
 * Selection is positional rather than content-based: allowed suffixes are
 * eligible at the flow root and recursively under exact first-level opt-in
 * directories. PDF is not allowed, and no content or size filter is applied.
 * The predicate is pure and receives POSIX-style relative paths from the
 * inventory built by `tree.mjs`.
 */

export const ALLOWED_EXTENSIONS = Object.freeze([
  '.md',
  '.sh',
  '.js',
  '.mjs',
  '.py',
  '.ts',
  '.ps1',
  '.json',
  '.yml',
  '.txt',
  '.jsonl',
]);

export const OPT_IN_DIRECTORIES = Object.freeze([
  'evidencia',
  'runs',
  'decisiones',
]);

/**
 * @param {string} relativePath path relative to the flow root, using `/`.
 * @returns {boolean} whether the path belongs to the document frontier.
 */
export function isCopiable(relativePath) {
  if (typeof relativePath !== 'string') return false;

  const segments = relativePath.split('/');
  if (segments.length > 1 && !OPT_IN_DIRECTORIES.includes(segments[0])) return false;

  const basename = segments.at(-1);
  if (!basename) return false;

  const lowercaseBasename = basename.toLowerCase();
  return ALLOWED_EXTENSIONS.some(
    (extension) => basename.length > extension.length && lowercaseBasename.endsWith(extension),
  );
}

/**
 * Detects Markdown paths whose immediate parent is the reserved `sdd` segment.
 * Callers apply this guard only to selected paths during first publication.
 *
 * @param {string} relativePath POSIX-style relative path.
 * @returns {boolean} whether the path collides with the vault node namespace.
 */
export function isReservedDocumentPath(relativePath) {
  if (typeof relativePath !== 'string') return false;

  const segments = relativePath.split('/');
  const basename = segments.at(-1);
  return segments.length > 1 && segments.at(-2) === 'sdd' && basename.endsWith('.md');
}

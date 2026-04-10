/**
 * Repair common LLM formatting glitches before markdown/KaTeX (fragmented lines,
 * spaced-out letters, weak matrix row breaks).
 */

const SINGLE_ASCII_TOKEN = /^[a-zA-Z0-9=+\-^./\\:;,!?]$/

/** Single visible character (ASCII token or any Unicode letter/number). */
function isSingleCharMergeToken(t: string): boolean {
  if (t.length !== 1) return false
  if (SINGLE_ASCII_TOKEN.test(t)) return true
  return /\p{L}|\p{N}/u.test(t)
}

/**
 * Merge lines that are a single character onto a previous content line (iterative).
 * Skips blank lines when finding the target so "For an\\n\\nm\\nt" still becomes "For an mt…".
 */
export function joinSingleCharLines(s: string): string {
  let prev = ''
  let out = s
  while (out !== prev) {
    prev = out
    const lines = out.split('\n')
    const merged: string[] = []
    for (const line of lines) {
      const t = line.trim()
      if (merged.length > 0 && isSingleCharMergeToken(t)) {
        let j = merged.length - 1
        let crossedBlank = false
        while (j >= 0 && merged[j].trim() === '') {
          crossedBlank = true
          j--
        }
        if (j >= 0) {
          const base = merged[j]
          const end = base.trimEnd()
          const spacer =
            crossedBlank && end.length > 0 && /[a-zA-Z0-9)=+\-^./\]}]$/u.test(end) && /\p{L}|\p{N}/u.test(t)
              ? ' '
              : ''
          merged[j] = base + spacer + t
          continue
        }
      }
      merged.push(line)
    }
    out = merged.join('\n')
  }
  return out
}

/**
 * Lines like "S e t t h i s t o z e r o :" → collapse spaces between single letters.
 */
export function collapseSpacedLetterLines(s: string): string {
  return s
    .split('\n')
    .map((line) => {
      const lead = line.match(/^\s*/)?.[0] ?? ''
      const t = line.trim()
      if (t.length < 9) return line
      const tokens = t.split(/\s+/).filter(Boolean)
      if (tokens.length < 5) return line
      const singleLetter = tokens.filter((x) => /^[a-zA-Z]$/.test(x)).length
      if (singleLetter / tokens.length < 0.65) return line
      let out = t
      let p = ''
      while (out !== p) {
        p = out
        out = out.replace(/([A-Za-z])\s+(?=[A-Za-z])/g, '$1')
      }
      return lead + out
    })
    .join('\n')
}

/**
 * Fix `0 \ 1` and `}\ 4` style row breaks inside matrices (should be `\\`).
 * The `}\ …` rule only runs when the next token is a digit or `-` so we do not
 * corrupt `}\ \frac` / `}\ \begin` (space + command after `}`).
 */
export function fixWeakMatrixRowBreaks(s: string): string {
  let out = s.replace(/(\d)\s*\\\s+(?=[\d\-\\])/g, '$1 \\\\ ')
  out = out.replace(/(\d)\s*\\\s+(?=\\end\{)/g, '$1 \\\\ ')
  out = out.replace(/([}\]])\s*\\\s+(?=[\d\-])/g, '$1 \\\\ ')
  return out
}

/** Collapse `A\nA\n` / `Σ\nΣ` duplicate single-letter lines (common LLM glitch). */
export function dedupeAdjacentSingleLetterLines(s: string): string {
  return s.replace(/(^|\n)(\p{L})\n\2(?=\n|$)/gmu, '$1$2')
}

/** Collapse 3+ consecutive blank lines to double newline. */
export function collapseBlankRuns(s: string): string {
  return s.replace(/\n{3,}/g, '\n\n')
}

/**
 * When text still contains literal "\\n" / "\\t" (model or double-encoded JSON).
 * Exam questions often ship as one line with many \\n and stray "\\ " before capitals.
 */
function decodeEscapedNewlines(s: string): string {
  if (!s.includes('\\n') && !s.includes('\\t')) return s
  const realLines = s.split('\n').length
  const fakeNL = (s.match(/\\n/g) || []).length
  const looksLessonBlob = realLines <= 2 && /#/.test(s)
  const looksExamOrChat =
    fakeNL > 0 &&
    (fakeNL >= 3 ||
      fakeNL >= Math.max(1, realLines - 1) ||
      /Question\s+\d+|points\)|\\n\\\s|SVD\s*\\|matrix.*\\n/i.test(s) ||
      (realLines <= 6 && fakeNL >= 2 && /matrix|Compute\s+the|singular\s+value/i.test(s)))
  if (!looksLessonBlob && !looksExamOrChat) return s
  let t = s.replace(/\\n+/g, '\n').replace(/\\t/g, '\t')
  t = t.replace(/^\s*\\\s+/gm, '')
  t = t.replace(/\n\\\s*(?=\n|$)/g, '\n')
  return t
}

/**
 * "SVD\\ Compute" / "decomposition\\ Provide" → period + space (not `a\\ Sigma`).
 * Requires Capital+lowercase after the gap so we skip `matrix\\ begin`-style TeX.
 */
function fixStrayBackslashBeforeCapitals(s: string): string {
  let out = s.replace(/([A-Za-z]{2,})\\ +(?=[A-Z][a-z])/g, '$1. ')
  out = out.replace(/([.!?])\s*\\\s+(?=[A-Z])/g, '$1 ')
  return out
}

/**
 * CommonMark needs ≥4 spaces before a block under a list item; models often use 2 before $$.
 */
export function fixListFollowedByDisplayMathIndent(s: string): string {
  return s.replace(
    /(^|\n)([ \t]*(?:[-*+]|\d+\.)\s+[^\n]+?:[ \t]*)\n([ \t]{1,3})(\$\$)/gm,
    '$1$2\n    $4',
  )
}

/**
 * Convert LaTeX \\(...\\) / \\[...\\] to $ / $$ for remark-math.
 * - Collapse \\( → \\( when over-escaped (JSON).
 * - Apply \\(...\\) per line so .+? cannot swallow newlines inside $$...$$ blocks.
 * - \\[...\\] stays whole-string (display) but avoids \\[4pt] via lookbehind.
 */
export function normalizeLatexDelimiters(src: string): string {
  let out = src.replace(/(?<!\\)\\\\\(/g, '\\(').replace(/(?<!\\)\\\\\)/g, '\\)')
  const lines = out.split('\n')
  out = lines
    .map((line) => line.replace(/\\\((.+?)\\\)/g, (_m, inner) => `$${inner}$`))
    .join('\n')
  out = out.replace(/(?<!\\)\\\[(.+?)(?<!\\)\\\]/gs, (_m, inner) => `$$${inner}$$`)
  return out
}

/** Full pipeline for assistant / solution / lesson bodies from the model. */
export function sanitizeLlmMarkdown(raw: string): string {
  let s = raw.replace(/\r\n/g, '\n')
  s = decodeEscapedNewlines(s)
  s = fixStrayBackslashBeforeCapitals(s)
  s = dedupeAdjacentSingleLetterLines(s)
  s = joinSingleCharLines(s)
  s = collapseSpacedLetterLines(s)
  s = joinSingleCharLines(s)
  s = fixWeakMatrixRowBreaks(s)
  s = fixListFollowedByDisplayMathIndent(s)
  s = normalizeLatexDelimiters(s)
  s = collapseBlankRuns(s)
  return s.trim()
}

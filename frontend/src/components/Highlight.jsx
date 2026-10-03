const LABEL = { SPELLING: 'Spelling', GRAMMAR: 'Grammar', INCORRECT_CONTENT: 'Incorrect / irrelevant' }

/** Renders the answer text with mistakes highlighted using the offsets returned by the AI service. */
export function buildSegments(text, mistakes) {
  const spans = (mistakes || [])
    .filter((m) => m.startOffset != null && m.endOffset != null && m.endOffset > m.startOffset && m.endOffset <= text.length)
    .sort((a, b) => a.startOffset - b.startOffset)
  const out = []
  let pos = 0
  for (const m of spans) {
    if (m.startOffset < pos) continue
    if (m.startOffset > pos) out.push({ text: text.slice(pos, m.startOffset) })
    out.push({ text: text.slice(m.startOffset, m.endOffset), mistake: m })
    pos = m.endOffset
  }
  if (pos < text.length) out.push({ text: text.slice(pos) })
  return out
}

export default function Highlight({ text, mistakes }) {
  if (!text) return <div className="text-muted fst-italic">No answer detected.</div>
  return (
    <div className="answer-box">
      {buildSegments(text, mistakes).map((s, i) =>
        s.mistake ? (
          <mark key={i} className={`m-${s.mistake.type}`} title={`${LABEL[s.mistake.type] || s.mistake.type}: ${s.mistake.description}${s.mistake.suggestion ? ' -> ' + s.mistake.suggestion : ''}`}>
            {s.text}
          </mark>
        ) : (
          <span key={i}>{s.text}</span>
        ),
      )}
    </div>
  )
}

export function HighlightLegend() {
  return (
    <div className="small text-muted mb-2">
      <mark className="m-SPELLING">Spelling</mark> <mark className="m-GRAMMAR">Grammar</mark>{' '}
      <mark className="m-INCORRECT_CONTENT">Incorrect / irrelevant</mark>
    </div>
  )
}

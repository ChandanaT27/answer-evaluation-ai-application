import { describe, expect, it } from 'vitest'
import { buildSegments } from './Highlight.jsx'

describe('buildSegments', () => {
  it('splits text around mistakes using offsets', () => {
    const segs = buildSegments('The proces is good', [{ startOffset: 4, endOffset: 10, type: 'SPELLING' }])
    expect(segs.map((s) => s.text)).toEqual(['The ', 'proces', ' is good'])
    expect(segs[1].mistake.type).toBe('SPELLING')
  })
  it('ignores overlapping and out-of-range mistakes', () => {
    const segs = buildSegments('abcdef', [
      { startOffset: 0, endOffset: 3, type: 'A' }, { startOffset: 2, endOffset: 4, type: 'B' }, { startOffset: 5, endOffset: 99, type: 'C' },
    ])
    expect(segs.filter((s) => s.mistake).map((s) => s.mistake.type)).toEqual(['A'])
  })
})

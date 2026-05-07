import { describe, it, expect } from 'vitest'
import { selectScoreline } from '@/lib/scoreline'
import type { Scoreline } from '@/lib/types'

function sc(scoreline: string, probability = 0.1): Scoreline {
  return { scoreline, probability }
}

describe('selectScoreline', () => {
  describe('matching scoreline found in top list', () => {
    it('returns away-win scoreline when dominant is A', () => {
      const top = [sc('1-0'), sc('0-0'), sc('0-1'), sc('2-0')]
      expect(selectScoreline('A', top, 1.2, 0.8)).toEqual([0, 1])
    })

    it('returns home-win scoreline when dominant is H', () => {
      const top = [sc('0-1'), sc('0-0'), sc('2-1'), sc('0-2')]
      expect(selectScoreline('H', top, 1.5, 0.8)).toEqual([2, 1])
    })

    it('returns draw scoreline when dominant is D', () => {
      const top = [sc('1-0'), sc('1-1'), sc('2-0')]
      expect(selectScoreline('D', top, 1.0, 1.0)).toEqual([1, 1])
    })

    it('skips scorelines where total goals > 6', () => {
      const top = [sc('4-3'), sc('0-1')]
      expect(selectScoreline('A', top, 1.0, 1.5)).toEqual([0, 1])
    })
  })

  describe('no matching scoreline — synthesise from xG', () => {
    it('synthesises away win when dominant is A and all scorelines are home wins', () => {
      const top = [sc('1-0'), sc('2-0'), sc('2-1'), sc('3-0'), sc('3-1')]
      // h=min(3,round(1.2))=1, a=min(3,round(0.8))=1 → a not > h → [h, h+1]=[1,2]
      expect(selectScoreline('A', top, 1.2, 0.8)).toEqual([1, 2])
    })

    it('synthesises home win when dominant is H and all scorelines are draws', () => {
      const top = [sc('0-0'), sc('1-1'), sc('2-2')]
      // h=min(3,round(1.5))=2, a=min(3,round(0.5))=1 → h>a → [2,1]
      expect(selectScoreline('H', top, 1.5, 0.5)).toEqual([2, 1])
    })

    it('synthesises draw when dominant is D and no draws in list', () => {
      const top = [sc('1-0'), sc('0-1'), sc('2-1')]
      // h=min(3,round(1.8))=2, a=min(3,round(1.3))=1 → d=min(2,1)=1 → [1,1]
      expect(selectScoreline('D', top, 1.8, 1.3)).toEqual([1, 1])
    })

    it('caps xG rounding at 3 before synthesis', () => {
      const top = [sc('0-1'), sc('0-2')]
      // h=min(3,round(4.8))=3, a=min(3,round(4.2))=3 → h not > a → [a+1,a]=[4,3]
      expect(selectScoreline('H', top, 4.8, 4.2)).toEqual([4, 3])
    })
  })
})

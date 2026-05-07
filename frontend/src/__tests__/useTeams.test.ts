import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTeams } from '@/hooks/useTeams'
import * as api from '@/lib/api'

vi.mock('@/lib/api')

const mockFetchTeams = vi.mocked(api.fetchTeams)

const mockTeam = {
  canonical_name: 'Brazil',
  display_name: 'Brazil',
  confederation: 'CONMEBOL' as const,
  fifa_rank: 1,
  aliases: [],
  is_known: true,
  default_metadata: {},
}

describe('useTeams', () => {
  beforeEach(() => mockFetchTeams.mockReset())

  it('starts with loading=true and empty teams array', async () => {
    let resolve!: (v: typeof mockTeam[]) => void
    mockFetchTeams.mockReturnValue(new Promise(r => { resolve = r }))
    const { result } = renderHook(() => useTeams())
    expect(result.current.loading).toBe(true)
    expect(result.current.teams).toEqual([])
    expect(result.current.error).toBeNull()
    // Resolve so React can clean up the pending effect
    await act(async () => { resolve([]) })
  })

  it('sets teams and loading=false after successful fetch', async () => {
    mockFetchTeams.mockResolvedValue([mockTeam])
    const { result } = renderHook(() => useTeams())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.teams).toEqual([mockTeam])
    expect(result.current.error).toBeNull()
  })

  it('sets error and loading=false on failed fetch', async () => {
    mockFetchTeams.mockRejectedValueOnce(new Error('Network error'))
    const { result } = renderHook(() => useTeams())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('Network error')
    expect(result.current.teams).toEqual([])
  })
})

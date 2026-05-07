import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import ProbabilityBars from '@/components/ProbabilityBars'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, initial, animate, transition, ...rest }: any) =>
      React.createElement('div', rest, children),
  },
}))

describe('ProbabilityBars', () => {
  const baseProps = {
    probabilities: { home_win: 0.5, draw: 0.25, away_win: 0.25 },
    homeTeam: 'Brazil',
    awayTeam: 'Argentina',
  }

  it('renders home team, away team, and draw labels', () => {
    render(<ProbabilityBars {...baseProps} />)
    expect(screen.getByText('Brazil')).toBeInTheDocument()
    expect(screen.getByText('Argentina')).toBeInTheDocument()
    expect(screen.getByText('Draw')).toBeInTheDocument()
  })

  it('renders correct percentage values', () => {
    render(<ProbabilityBars {...baseProps} />)
    expect(screen.getByText('50.0%')).toBeInTheDocument()
    const quarters = screen.getAllByText('25.0%')
    expect(quarters).toHaveLength(2)
  })

  it('shows malformed warning when probabilities do not sum to 1', () => {
    render(
      <ProbabilityBars
        probabilities={{ home_win: 0.5, draw: 0.4, away_win: 0.4 }}
        homeTeam="Brazil"
        awayTeam="Argentina"
      />
    )
    expect(screen.getByText(/probabilities sum to/i)).toBeInTheDocument()
  })

  it('does not show malformed warning for valid probabilities', () => {
    render(<ProbabilityBars {...baseProps} />)
    expect(screen.queryByText(/probabilities sum to/i)).not.toBeInTheDocument()
  })
})

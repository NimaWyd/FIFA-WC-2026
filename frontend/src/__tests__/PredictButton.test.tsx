import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PredictButton from '@/components/PredictButton'

describe('PredictButton', () => {
  it('is disabled when loading=true', () => {
    render(<PredictButton loading={true} disabled={false} onClick={vi.fn()} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('is disabled when disabled=true', () => {
    render(<PredictButton loading={false} disabled={true} onClick={vi.fn()} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('calls onClick when neither loading nor disabled', async () => {
    const onClick = vi.fn()
    render(<PredictButton loading={false} disabled={false} onClick={onClick} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('shows "Predicting…" text when loading', () => {
    render(<PredictButton loading={true} disabled={false} onClick={vi.fn()} />)
    expect(screen.getByText('Predicting…')).toBeInTheDocument()
  })

  it('shows "Predict Match" text when not loading', () => {
    render(<PredictButton loading={false} disabled={false} onClick={vi.fn()} />)
    expect(screen.getByText('Predict Match')).toBeInTheDocument()
  })
})

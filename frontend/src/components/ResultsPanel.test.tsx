import { fireEvent, render, screen, within } from '@testing-library/react';
import { getDemoResult } from '../lib/fixtures';
import { NOVEL_CLIMATE_WARNING } from '../lib/headline';
import { DEMO_BANNER, ResultsPanel } from './ResultsPanel';

describe('ResultsPanel', () => {
  it('normal case: demo banner, best-match headline, text list, fingerprint table', () => {
    const onSelect = vi.fn();
    render(<ResultsPanel result={getDemoResult('fake-colfax')} selectedRank={null} onSelect={onSelect} />);
    expect(screen.getByText(DEMO_BANNER)).toBeInTheDocument();
    expect(screen.getByText(/^Best match: rank 1, strong match/)).toBeInTheDocument();
    expect(screen.queryByText(NOVEL_CLIMATE_WARNING)).not.toBeInTheDocument();
    const list = screen.getByRole('list', { name: /Matching places/ });
    expect(within(list).getAllByRole('button')).toHaveLength(20);
    fireEvent.click(within(list).getAllByRole('button')[1]!);
    expect(onSelect).toHaveBeenCalledWith(2);
    expect(screen.getByText('Jan–Mar average temperature')).toBeInTheDocument();
    expect(screen.getAllByText('2.6 °C (36.7 °F)').length).toBeGreaterThan(0);
    expect(screen.getByText('1995–2014 → 2041–2060')).toBeInTheDocument();
  });

  it('novel case: shows the warning instead of a best-match headline', () => {
    render(<ResultsPanel result={getDemoResult('fake-lind')} selectedRank={1} onSelect={() => {}} />);
    expect(screen.getByRole('alert')).toHaveTextContent(NOVEL_CLIMATE_WARNING);
    expect(screen.queryByText(/^Best match/)).not.toBeInTheDocument();
  });

  it('shows notes when present and hides the demo banner for computed results', () => {
    const r = { ...getDemoResult('fake-colfax'), source: 'computed' as const, notes: ['Soil data is approximate.'] };
    render(<ResultsPanel result={r} selectedRank={null} onSelect={() => {}} />);
    expect(screen.getByText('About this result')).toBeInTheDocument();
    expect(screen.getByText('Soil data is approximate.')).toBeInTheDocument();
    expect(screen.queryByText(DEMO_BANNER)).not.toBeInTheDocument();
  });
});

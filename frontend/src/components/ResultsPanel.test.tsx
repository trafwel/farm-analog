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

  it('shows a match score ring per place and keeps sigma and model agreement in the details', () => {
    const { container } = render(
      <ResultsPanel result={getDemoResult('fake-colfax')} selectedRank={null} onSelect={() => {}} />,
    );
    const list = screen.getByRole('list', { name: /Matching places/ });
    expect(within(list).getAllByRole('img', { name: /^Match score \d+ out of 100/ })).toHaveLength(20);
    expect(within(list).getAllByRole('img')[0]).toHaveAccessibleName('Match score 92 out of 100: strong match');
    expect(list).not.toHaveTextContent(/sigma|models agree/i);
    const details = container.querySelector('details.result-details')!;
    expect(details).not.toHaveAttribute('open');
    expect(within(details as HTMLElement).getByText('Result Details')).toBeInTheDocument();
    expect(details).toHaveTextContent('0.51');
    expect(details).toHaveTextContent(/climate models agree/);
    // Outside the details, nothing mentions sigma.
    const rest = container.cloneNode(true) as HTMLElement;
    rest.querySelector('details.result-details')!.remove();
    expect(rest).not.toHaveTextContent(/sigma/i);
  });

  it('novel case: shows the warning instead of a best-match headline', () => {
    render(<ResultsPanel result={getDemoResult('fake-lind')} selectedRank={1} onSelect={() => {}} />);
    expect(screen.getByRole('alert')).toHaveTextContent(NOVEL_CLIMATE_WARNING);
    expect(screen.queryByText(/^Best match/)).not.toBeInTheDocument();
  });

  it('puts notes inside Result Details and hides the demo banner for computed results', () => {
    const r = { ...getDemoResult('fake-colfax'), source: 'computed' as const, notes: ['Soil data is approximate.'] };
    const { container } = render(<ResultsPanel result={r} selectedRank={null} onSelect={() => {}} />);
    const details = container.querySelector('details.result-details') as HTMLElement;
    expect(within(details).getByText('About this result')).toBeInTheDocument();
    expect(within(details).getByText('Soil data is approximate.')).toBeInTheDocument();
    expect(screen.getAllByText('About this result')).toHaveLength(1);
    expect(screen.queryByText(DEMO_BANNER)).not.toBeInTheDocument();
  });

  it('has no score-range explanation above the results', () => {
    const { container } = render(
      <ResultsPanel result={getDemoResult('fake-colfax')} selectedRank={null} onSelect={() => {}} />,
    );
    const headline = container.querySelector('.headline')!;
    expect(headline.nextElementSibling).toHaveClass('meta');
    expect(headline.parentElement).not.toHaveTextContent(/70 to 84 good, 50 to 69 weak\./);
  });
});

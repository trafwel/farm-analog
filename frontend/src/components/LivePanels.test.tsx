import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fireEvent, render, screen, within } from '@testing-library/react';
import type { AnalogResult } from '../types/contract';
import { getDemoResult } from '../lib/fixtures';
import { ResultsPanel } from './ResultsPanel';
import { NEEDS_LIVE } from './PlaceComparison';
import { LOCAL_EXPERT } from './Glossary';

/** A real saved Earth Engine result for the Cook test field (M11). */
const cook = JSON.parse(
  readFileSync(resolve(__dirname, '../../../data/samples/live_cook_ssp245.json'), 'utf8'),
) as AnalogResult;

describe('M8 panels on a live result', () => {
  it('shows rotation cards with the current rotation first', () => {
    render(<ResultsPanel result={cook} selectedRank={null} onSelect={() => {}} />);
    const section = screen.getByRole('region', { name: /Rotation options/ });
    const items = within(section).getAllByRole('listitem').filter((li) => li.classList.contains('rotation'));
    expect(items.length).toBeGreaterThanOrEqual(3);
    expect(items[0]).toHaveTextContent('Your field now');
    expect(items[0]).toHaveTextContent(cook.rotations![0]!.name);
    expect(section).toHaveTextContent('Check with your county extension agent');
  });

  it('sorts rotation options by the farmer’s priorities, current rotation first', () => {
    const colfax = JSON.parse(
      readFileSync(resolve(__dirname, '../../../data/samples/live_colfax_ssp245.json'), 'utf8'),
    ) as AnalogResult;
    render(<ResultsPanel result={colfax} selectedRank={null} onSelect={() => {}} />);
    const section = screen.getByRole('region', { name: /Rotation options/ });
    const names = () => within(section).getAllByRole('heading', { level: 4 }).map((h) => h.textContent);
    expect(names()[1]).toContain('Flexible mix of fallow');
    fireEvent.click(within(section).getByRole('checkbox', { name: 'Add nitrogen' }));
    expect(names()[0]).toContain('Winter wheat → Barley → Pulses');
    expect(names()[1]).toContain('Winter wheat → Spring wheat → Pulses');
    expect(section).toHaveTextContent('nitrogen-fixing crop in 1 of 3 years');
    expect(within(section).getAllByText('Best fit for your choices')).toHaveLength(2);
    expect(section).toHaveTextContent('Income, markets and equipment aren’t measured here');
  });

  it('compares the best match by default, then the selected place', () => {
    const { rerender } = render(<ResultsPanel result={cook} selectedRank={null} onSelect={() => {}} />);
    const best = cook.analogs[0]!;
    expect(screen.getByRole('heading', { name: `Compare with rank 1: ${best.place_name}` })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Average temperature by month/ })).toBeInTheDocument();
    expect(screen.getByText(/What grows there/)).toBeInTheDocument();
    const hazards = screen.getByRole('table', { name: /Hazard outlook/ });
    expect(hazards).toHaveTextContent('Hot days above 32 °C');
    expect(hazards).toHaveTextContent('18 days');
    expect(hazards).toHaveTextContent('28 days');
    expect(hazards).toHaveTextContent('Soil water in the driest month');
    expect(hazards).toHaveTextContent('16.6% (Sep)');
    expect(screen.getByRole('img', { name: /Root-zone soil water by month/ })).toBeInTheDocument();
    rerender(<ResultsPanel result={cook} selectedRank={2} onSelect={() => {}} />);
    expect(screen.getByRole('heading', { name: /Compare with rank 2/ })).toBeInTheDocument();
  });

  it('a place without details says how to get them', () => {
    render(<ResultsPanel result={cook} selectedRank={10} onSelect={() => {}} />);
    expect(screen.getByText(NEEDS_LIVE)).toBeInTheDocument();
  });

  it('shows Bill’s summary as plain text and the glossary', () => {
    render(
      <ResultsPanel
        result={cook}
        selectedRank={null}
        onSelect={() => {}}
        billSummary={{ text: '<b>not bold</b> Summary.', source: 'template', notices: [] }}
      />,
    );
    expect(screen.getByText('<b>not bold</b> Summary.')).toBeInTheDocument();
    expect(screen.getByText(/fixed template/)).toBeInTheDocument();
  });

  it('labels a saved Gemini summary with its model and date', () => {
    render(
      <ResultsPanel
        result={cook}
        selectedRank={null}
        onSelect={() => {}}
        billSummary={{ text: 'Saved.', source: 'gemini', notices: [], model: 'gemini-x', generated: '2026-11-15' }}
      />,
    );
    expect(screen.getByText(/Written ahead of time by Bill \(Gemini, gemini-x\) for this test field on 2026-11-15/)).toBeInTheDocument();
    expect(screen.getByText(LOCAL_EXPERT)).toBeInTheDocument();
  });

  it('demo data without rotations or hazards hides those sections', () => {
    render(<ResultsPanel result={getDemoResult('fake-colfax')} selectedRank={null} onSelect={() => {}} />);
    expect(screen.queryByRole('region', { name: /Rotation options/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('table', { name: /Hazard outlook/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /Rank 2/ })[0]!);
  });
});

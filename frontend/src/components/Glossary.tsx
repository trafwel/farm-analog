export const GLOSSARY: { term: string; meaning: string }[] = [
  {
    term: 'Analog (matching place)',
    meaning:
      'A place whose climate today is close to your field’s projected climate around 2050. What farmers there do now has already been tried in that climate.',
  },
  {
    term: 'Sigma',
    meaning:
      'How different two climates are, measured in your field’s normal year-to-year swings. Below 1 is like an ordinary year at your field; 4 or more means no real match.',
  },
  {
    term: 'Climate models agreeing',
    meaning:
      'We run 8 NASA-downscaled climate models (NEX-GDDP-CMIP6). A place counts as agreed by a model when it is a good match (sigma below 2) under that model’s future.',
  },
  {
    term: 'SSP2-4.5 and SSP5-8.5',
    meaning:
      'Emissions scenarios: SSP2-4.5 is moderate (current policies roughly continue); SSP5-8.5 is high (emissions keep rising).',
  },
  {
    term: 'NDVI',
    meaning:
      'A satellite measure of green plant cover (Landsat). Low values mean bare soil or stubble, which is more exposed to wind and water erosion.',
  },
  {
    term: 'Root-zone soil moisture (SMAP)',
    meaning:
      'How much water the top 1 m of soil holds, as a share of its volume, from NASA’s SMAP satellite combined with a land model. It is an average over a ~9 km grid cell, not a reading from your field; a soil probe or your own records show your field’s soil.',
  },
  {
    term: 'Frost-free season',
    meaning: 'Days between the average last spring frost and first fall frost (minimum temperature at or below 0 °C).',
  },
  {
    term: 'Fallow',
    meaning: 'A year with no crop, used in dry areas to store soil water for the next crop.',
  },
  {
    term: 'Nitrogen-fixing crop',
    meaning: 'Peas, lentils, chickpeas and other legumes, which add nitrogen to the soil for the next crop.',
  },
];

export const LOCAL_EXPERT =
  'This tool shows patterns in public data. It does not replace your judgment or local expertise: check any change with your county extension agent, crop adviser or neighbors who farm the matching places.';

export function Glossary() {
  return (
    <section className="card" aria-labelledby="glossary-heading">
      <h3 id="glossary-heading">Words used here</h3>
      <dl className="glossary">
        {GLOSSARY.map((g) => (
          <div key={g.term}>
            <dt>{g.term}</dt>
            <dd>{g.meaning}</dd>
          </div>
        ))}
      </dl>
      <p className="small local-expert">{LOCAL_EXPERT}</p>
    </section>
  );
}

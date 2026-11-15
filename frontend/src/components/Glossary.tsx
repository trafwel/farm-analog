export const GLOSSARY: { term: string; meaning: string }[] = [
  {
    term: 'Analog (matching place)',
    meaning:
      'A place whose climate today is close to your field’s projected climate around 2050. What farmers there do now has already been tried in that climate.',
  },
  {
    term: 'Match score',
    meaning:
      'How close a place’s climate today is to your field’s projected climate, from 0 to 100. 85 and above is a strong match, 70 to 84 good, 50 to 69 weak, and below 50 no real match. The numbers behind it are under Result Details.',
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
    term: 'Afternoon ground temperature (ECOSTRESS)',
    meaning:
      'The temperature of the ground or crop surface, measured at 70 m by NASA’s ECOSTRESS instrument on the space station on clear summer afternoons. It is not air temperature: a dry or bare surface can be 10 °C hotter than the air, and a green, well-watered crop stays cooler. That is why June (crops growing) and July–August (mostly stubble and fallow after harvest) are shown separately.',
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

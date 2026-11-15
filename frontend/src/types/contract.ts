/* eslint-disable */
/**
 * GENERATED FILE - do not edit by hand. Run `pnpm gen:types` to regenerate.
 * Source: contract/*.schema.json (Pydantic, JSON Schema 2020-12), with
 * `prefixItems` tuples rewritten to draft-07 `items` arrays (see scripts/gen-types.mjs).
 */

// ---- AnalogRequest (../contract/analog_request.schema.json) ----
/**
 * @minItems 1
 */
export type Coordinates = [[number, number][], ...[number, number][][]];
export type Type = "Polygon";
export type Scenario = "ssp245" | "ssp585";
export type TopN = number;

/**
 * Find analogs for one field.
 */
export interface AnalogRequest {
  field: PolygonGeometry;
  scenario?: Scenario;
  top_n?: TopN;
}
/**
 * A GeoJSON Polygon: the farmer's field as drawn on the map.
 */
export interface PolygonGeometry {
  coordinates: Coordinates;
  type: Type;
}

// ---- AnalogResult (../contract/analog_result.schema.json) ----
/**
 * @minItems 12
 * @maxItems 12
 */
export type Ppt = [number, number, number, number, number, number, number, number, number, number, number, number];
/**
 * @minItems 12
 * @maxItems 12
 */
export type Tmean = [number, number, number, number, number, number, number, number, number, number, number, number];
export type Crops = CropShare[] | null;
export type Crop = string;
export type Share = number;
export type PptAmj = number;
export type PptJas = number;
export type PptJfm = number;
export type PptOnd = number;
export type TmeanAmj = number;
export type TmeanJas = number;
export type TmeanJfm = number;
export type TmeanOnd = number;
export type BareMonths = number[] | null;
export type ExtremeRainDays = number | null;
export type FirstFallFrostDoy = number | null;
export type FrostFreeDays = number | null;
export type HeatDays = number | null;
export type LastSpringFrostDoy = number | null;
export type Max1DayRainMm = number | null;
export type MissingSources = string[];
export type NdviMonthly = (number | null)[] | null;
export type SoilMoistureMonthly = (number | null)[] | null;
export type SurfacePasses = number | null;
export type SurfaceTempJulaugC = number | null;
export type SurfaceTempJuneC = number | null;
export type Lat = number;
export type Lon = number;
export type MatchQuality = "strong" | "good" | "weak" | "none";
export type ModelsAgree = number;
export type ModelsTotal = number;
export type PlaceName = string | null;
export type Rank = number;
export type Sigma = number;
export type AvailableWaterCapacityCm = number | null;
export type ClayPct = number | null;
export type DepthToRestrictiveLayerCm = number | null;
export type OrganicMatterPct = number | null;
export type SandPct = number | null;
export type Analogs = Analog[];
/**
 * @minItems 2
 * @maxItems 2
 */
export type BaselineYears = [number, number];
export type FieldId = string;
/**
 * @minItems 2
 * @maxItems 2
 */
export type FutureYears = [number, number];
/**
 * @minItems 1
 */
export type Models = [string, ...string[]];
export type Notes = string[];
export type NovelClimate = boolean;
export type Rotations = RotationStrategy[] | null;
export type AnalogShare = number;
export type AnalogsChecked = number;
export type AnalogsUsing = number;
export type Benefits = string[];
/**
 * @minItems 1
 */
export type Crops1 = [string, ...string[]];
export type Current = boolean;
export type Evidence = string[];
export type FieldShare = number | null;
export type Flexible = boolean;
export type Gaps = string[];
export type Name = string;
export type Risks = string[];
export type BreakCrop = number;
export type Fallow = number;
export type HighResidue = number;
export type HighWater = number;
export type LowCover = number;
export type LowWater = number;
export type NFixing = number;
export type Years = number;
export type Why = string;
export type Source = "computed" | "fixture";

/**
 * Everything the app shows for one field.
 */
export interface AnalogResult {
  analogs: Analogs;
  baseline_years: BaselineYears;
  farm_future: SeasonalFingerprint;
  farm_hazards?: Hazards | null;
  farm_soil?: SoilProfile | null;
  farm_today: SeasonalFingerprint;
  field_id: FieldId;
  future_years: FutureYears;
  models: Models;
  notes?: Notes;
  novel_climate: NovelClimate;
  rotations?: Rotations;
  scenario: Scenario;
  source: Source;
}
/**
 * One place whose climate today matches the farm's future climate.
 */
export interface Analog {
  climograph?: Climograph | null;
  crops?: Crops;
  fingerprint: SeasonalFingerprint;
  hazards?: Hazards | null;
  lat: Lat;
  lon: Lon;
  match_quality: MatchQuality;
  models_agree: ModelsAgree;
  models_total: ModelsTotal;
  place_name?: PlaceName;
  rank: Rank;
  sigma: Sigma;
  soil?: SoilProfile | null;
}
/**
 * Data for the comparison chart: the farm today, the farm in the future, the analog today.
 */
export interface Climograph {
  analog_today: MonthlyClimate;
  farm_future: MonthlyClimate;
  farm_today: MonthlyClimate;
}
/**
 * Twelve monthly values, January first: mean temperature in °C, precipitation in mm.
 */
export interface MonthlyClimate {
  ppt: Ppt;
  tmean: Tmean;
}
export interface CropShare {
  crop: Crop;
  share: Share;
}
/**
 * The 8 climate values used for matching (definition in ``farm_analog.fingerprint``).
 *
 * For each calendar quarter: average temperature (``tmean_``, the mean of the three monthly
 * mean temperatures, °C) and total precipitation (``ppt_``, mm). Quarters: ``jfm`` =
 * Jan-Mar, ``amj`` = Apr-Jun, ``jas`` = Jul-Sep, ``ond`` = Oct-Dec.
 */
export interface SeasonalFingerprint {
  ppt_amj: PptAmj;
  ppt_jas: PptJas;
  ppt_jfm: PptJfm;
  ppt_ond: PptOnd;
  tmean_amj: TmeanAmj;
  tmean_jas: TmeanJas;
  tmean_jfm: TmeanJfm;
  tmean_ond: TmeanOnd;
}
/**
 * Hazard history and field conditions at one place (M13), from PRISM daily (heat, frost;
 * 1995-2014), NASA GPM IMERG (extreme rain; 2014-2023), NASA SMAP L4 (root-zone soil
 * moisture; 2016-2023), Landsat 8/9 (NDVI; 2019-2023) and NASA ECOSTRESS (afternoon surface
 * temperature; 2018-2025). Any value may be missing.
 */
export interface Hazards {
  bare_months?: BareMonths;
  extreme_rain_days?: ExtremeRainDays;
  first_fall_frost_doy?: FirstFallFrostDoy;
  frost_free_days?: FrostFreeDays;
  heat_days?: HeatDays;
  last_spring_frost_doy?: LastSpringFrostDoy;
  max_1day_rain_mm?: Max1DayRainMm;
  missing_sources?: MissingSources;
  ndvi_monthly?: NdviMonthly;
  soil_moisture_monthly?: SoilMoistureMonthly;
  surface_passes?: SurfacePasses;
  surface_temp_julaug_c?: SurfaceTempJulaugC;
  surface_temp_june_c?: SurfaceTempJuneC;
}
/**
 * Soil summary; any value can be missing where the soil survey has no data.
 */
export interface SoilProfile {
  available_water_capacity_cm?: AvailableWaterCapacityCm;
  clay_pct?: ClayPct;
  depth_to_restrictive_layer_cm?: DepthToRestrictiveLayerCm;
  organic_matter_pct?: OrganicMatterPct;
  sand_pct?: SandPct;
}
/**
 * One crop-rotation option (M12): the field's current rotation or one that farmers in the
 * analog areas use. Every text field is written by code from observed data and a fixed
 * crop-traits table, never by an LLM.
 */
export interface RotationStrategy {
  analog_share: AnalogShare;
  analogs_checked: AnalogsChecked;
  analogs_using: AnalogsUsing;
  benefits: Benefits;
  crops: Crops1;
  current?: Current;
  evidence: Evidence;
  field_share?: FieldShare;
  flexible?: Flexible;
  gaps: Gaps;
  name: Name;
  risks: Risks;
  traits?: RotationTraits | null;
  why: Why;
}
/**
 * Share of a rotation's years with each crop trait (M19), from the fixed crop-traits table
 * in ``rotations.TRAITS``. A cycle counts each year once; a flexible mix counts each of its
 * main crops as one year (an approximation, since their order and frequency vary). The
 * frontend scores farmer priorities from these numbers.
 */
export interface RotationTraits {
  break_crop: BreakCrop;
  fallow: Fallow;
  high_residue: HighResidue;
  high_water: HighWater;
  low_cover: LowCover;
  low_water: LowWater;
  n_fixing: NFixing;
  years: Years;
}

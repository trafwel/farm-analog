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
export type Source = "computed" | "fixture";

/**
 * Everything the app shows for one field.
 */
export interface AnalogResult {
  analogs: Analogs;
  baseline_years: BaselineYears;
  farm_future: SeasonalFingerprint;
  farm_soil?: SoilProfile | null;
  farm_today: SeasonalFingerprint;
  field_id: FieldId;
  future_years: FutureYears;
  models: Models;
  notes?: Notes;
  novel_climate: NovelClimate;
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
 * Soil summary; any value can be missing where the soil survey has no data.
 */
export interface SoilProfile {
  available_water_capacity_cm?: AvailableWaterCapacityCm;
  clay_pct?: ClayPct;
  depth_to_restrictive_layer_cm?: DepthToRestrictiveLayerCm;
  organic_matter_pct?: OrganicMatterPct;
  sand_pct?: SandPct;
}

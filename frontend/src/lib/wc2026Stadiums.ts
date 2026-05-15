export interface StadiumInfo {
  name: string;
  city: string;
  country: string;
  capacity: number;
  surface: string;
  imageUrl: string;
}

const W = "https://upload.wikimedia.org/wikipedia/commons/thumb";

export const WC2026_STADIUMS: Record<string, StadiumInfo> = {
  Atlanta: {
    name: "Mercedes-Benz Stadium",
    city: "Atlanta, GA",
    country: "USA",
    capacity: 71000,
    surface: "FieldTurf",
    imageUrl: `${W}/1/10/Mercedes_Benz_Stadium_time_lapse_capture_2017-08-13.jpg/1280px-Mercedes_Benz_Stadium_time_lapse_capture_2017-08-13.jpg`,
  },
  Boston: {
    name: "Gillette Stadium",
    city: "Foxborough, MA",
    country: "USA",
    capacity: 65878,
    surface: "Grass",
    imageUrl: `${W}/d/db/Gillette_Stadium_%28Top_View%29.jpg/1280px-Gillette_Stadium_%28Top_View%29.jpg`,
  },
  Dallas: {
    name: "AT&T Stadium",
    city: "Arlington, TX",
    country: "USA",
    capacity: 80000,
    surface: "AstroTurf",
    imageUrl: `${W}/1/11/Arlington_June_2020_4_%28AT%26T_Stadium%29.jpg/1280px-Arlington_June_2020_4_%28AT%26T_Stadium%29.jpg`,
  },
  Houston: {
    name: "NRG Stadium",
    city: "Houston, TX",
    country: "USA",
    capacity: 72220,
    surface: "FieldTurf",
    imageUrl: `${W}/3/3e/Nrg_stadium.jpg/1280px-Nrg_stadium.jpg`,
  },
  "Kansas City": {
    name: "GEHA Field at Arrowhead Stadium",
    city: "Kansas City, MO",
    country: "USA",
    capacity: 76416,
    surface: "Grass",
    imageUrl: `${W}/a/ac/Aerial_view_of_Arrowhead_Stadium_08-31-2013.jpg/1280px-Aerial_view_of_Arrowhead_Stadium_08-31-2013.jpg`,
  },
  "Los Angeles": {
    name: "SoFi Stadium",
    city: "Inglewood, CA",
    country: "USA",
    capacity: 70240,
    surface: "Bermuda grass",
    imageUrl: `${W}/b/b3/SoFi_Stadium_2023.jpg/1280px-SoFi_Stadium_2023.jpg`,
  },
  Miami: {
    name: "Hard Rock Stadium",
    city: "Miami Gardens, FL",
    country: "USA",
    capacity: 65326,
    surface: "Grass",
    imageUrl: `${W}/c/ce/Hard_Rock_Stadium_for_Super_Bowl_LIV_%2849606710103%29.jpg/1280px-Hard_Rock_Stadium_for_Super_Bowl_LIV_%2849606710103%29.jpg`,
  },
  "Mexico City": {
    name: "Estadio Azteca",
    city: "Mexico City",
    country: "Mexico",
    capacity: 87523,
    surface: "Grass",
    imageUrl: `${W}/0/07/Vista_a%C3%A9rea_del_Estadio_Azteca_-_2026_-_02.jpg/1280px-Vista_a%C3%A9rea_del_Estadio_Azteca_-_2026_-_02.jpg`,
  },
  Guadalajara: {
    name: "Estadio Akron",
    city: "Zapopan, Jalisco",
    country: "Mexico",
    capacity: 49850,
    surface: "Grass",
    imageUrl: `${W}/1/10/Estadio_Akron_02-07-2022_cabecera_sur_lado_derecho_%283%29.jpg/1280px-Estadio_Akron_02-07-2022_cabecera_sur_lado_derecho_%283%29.jpg`,
  },
  Monterrey: {
    name: "Estadio BBVA",
    city: "Guadalupe, Nuevo León",
    country: "Mexico",
    capacity: 53500,
    surface: "Grass",
    imageUrl: `${W}/5/57/Mexico_Guadalupe_Monterrey_Estadio_BBVA_Bancomer_fifa_world_cup_2026_6.JPG/1280px-Mexico_Guadalupe_Monterrey_Estadio_BBVA_Bancomer_fifa_world_cup_2026_6.JPG`,
  },
  "New York/New Jersey": {
    name: "MetLife Stadium",
    city: "East Rutherford, NJ",
    country: "USA",
    capacity: 82500,
    surface: "FieldTurf",
    imageUrl: `${W}/0/04/Metlife_stadium_%28Aerial_view%29.jpg/1280px-Metlife_stadium_%28Aerial_view%29.jpg`,
  },
  Philadelphia: {
    name: "Lincoln Financial Field",
    city: "Philadelphia, PA",
    country: "USA",
    capacity: 69796,
    surface: "Grass",
    imageUrl: `${W}/a/a1/Lincoln_Financial_Field_%28Aerial_view%29.jpg/1280px-Lincoln_Financial_Field_%28Aerial_view%29.jpg`,
  },
  "San Francisco": {
    name: "Levi's Stadium",
    city: "Santa Clara, CA",
    country: "USA",
    capacity: 68500,
    surface: "Grass",
    imageUrl: `${W}/a/a6/Levi%27s_Stadium_in_February_2016_prior_to_Super_Bowl_50_%2824398261729%29.jpg/1280px-Levi%27s_Stadium_in_February_2016_prior_to_Super_Bowl_50_%2824398261729%29.jpg`,
  },
  Seattle: {
    name: "Lumen Field",
    city: "Seattle, WA",
    country: "USA",
    capacity: 72000,
    surface: "FieldTurf",
    imageUrl: `${W}/5/53/Qwest_Field_North.jpg/1280px-Qwest_Field_North.jpg`,
  },
  Toronto: {
    name: "BMO Field",
    city: "Toronto, ON",
    country: "Canada",
    capacity: 30000,
    surface: "Grass",
    imageUrl: `${W}/9/91/Toronto_BMO_Field_in_2024.jpg/1280px-Toronto_BMO_Field_in_2024.jpg`,
  },
  Vancouver: {
    name: "BC Place",
    city: "Vancouver, BC",
    country: "Canada",
    capacity: 54500,
    surface: "FieldTurf",
    imageUrl: `${W}/f/ff/BC_Place_2015_Women%27s_FIFA_World_Cup.jpg/1280px-BC_Place_2015_Women%27s_FIFA_World_Cup.jpg`,
  },
};

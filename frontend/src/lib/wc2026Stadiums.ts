export interface StadiumInfo {
  name: string;
  city: string;
  country: string;
  capacity: number;
  surface: string;
  imageUrl: string;
}

function wikiImg(filename: string): string {
  return `https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${encodeURIComponent(filename)}&width=1280`;
}

export const WC2026_STADIUMS: Record<string, StadiumInfo> = {
  Atlanta: {
    name: "Mercedes-Benz Stadium",
    city: "Atlanta, GA",
    country: "USA",
    capacity: 71000,
    surface: "FieldTurf",
    imageUrl: wikiImg("Mercedes-Benz_Stadium.jpg"),
  },
  Boston: {
    name: "Gillette Stadium",
    city: "Foxborough, MA",
    country: "USA",
    capacity: 65878,
    surface: "Grass",
    imageUrl: wikiImg("Gillette_Stadium.jpg"),
  },
  Dallas: {
    name: "AT&T Stadium",
    city: "Arlington, TX",
    country: "USA",
    capacity: 80000,
    surface: "AstroTurf",
    imageUrl: wikiImg("AT&T_Stadium_by_D_Ramey_Logan.jpg"),
  },
  Houston: {
    name: "NRG Stadium",
    city: "Houston, TX",
    country: "USA",
    capacity: 72220,
    surface: "FieldTurf",
    imageUrl: wikiImg("NRG_Stadium.jpg"),
  },
  "Kansas City": {
    name: "GEHA Field at Arrowhead Stadium",
    city: "Kansas City, MO",
    country: "USA",
    capacity: 76416,
    surface: "Grass",
    imageUrl: wikiImg("Arrowhead_Stadium.jpg"),
  },
  "Los Angeles": {
    name: "SoFi Stadium",
    city: "Inglewood, CA",
    country: "USA",
    capacity: 70240,
    surface: "Bermuda grass",
    imageUrl: wikiImg("SoFi_Stadium.jpg"),
  },
  Miami: {
    name: "Hard Rock Stadium",
    city: "Miami Gardens, FL",
    country: "USA",
    capacity: 65326,
    surface: "Grass",
    imageUrl: wikiImg("Hard_Rock_Stadium.jpg"),
  },
  "Mexico City": {
    name: "Estadio Azteca",
    city: "Mexico City",
    country: "Mexico",
    capacity: 87523,
    surface: "Grass",
    imageUrl: wikiImg("Azteca_Stadium.jpg"),
  },
  Guadalajara: {
    name: "Estadio Akron",
    city: "Zapopan, Jalisco",
    country: "Mexico",
    capacity: 49850,
    surface: "Grass",
    imageUrl: wikiImg("Estadio_Akron.jpg"),
  },
  Monterrey: {
    name: "Estadio BBVA",
    city: "Guadalupe, Nuevo León",
    country: "Mexico",
    capacity: 53500,
    surface: "Grass",
    imageUrl: wikiImg("Estadio_BBVA.jpg"),
  },
  "New York/New Jersey": {
    name: "MetLife Stadium",
    city: "East Rutherford, NJ",
    country: "USA",
    capacity: 82500,
    surface: "FieldTurf",
    imageUrl: wikiImg("MetLife_Stadium.jpg"),
  },
  Philadelphia: {
    name: "Lincoln Financial Field",
    city: "Philadelphia, PA",
    country: "USA",
    capacity: 69796,
    surface: "Grass",
    imageUrl: wikiImg("Lincoln_Financial_Field.jpg"),
  },
  "San Francisco": {
    name: "Levi's Stadium",
    city: "Santa Clara, CA",
    country: "USA",
    capacity: 68500,
    surface: "Grass",
    imageUrl: wikiImg("Levi's_Stadium.jpg"),
  },
  Seattle: {
    name: "Lumen Field",
    city: "Seattle, WA",
    country: "USA",
    capacity: 72000,
    surface: "FieldTurf",
    imageUrl: wikiImg("Lumen_Field.jpg"),
  },
  Toronto: {
    name: "BMO Field",
    city: "Toronto, ON",
    country: "Canada",
    capacity: 30000,
    surface: "Grass",
    imageUrl: wikiImg("BMO_Field.jpg"),
  },
  Vancouver: {
    name: "BC Place",
    city: "Vancouver, BC",
    country: "Canada",
    capacity: 54500,
    surface: "FieldTurf",
    imageUrl: wikiImg("BC_Place.jpg"),
  },
};

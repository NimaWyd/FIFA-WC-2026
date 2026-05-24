// Run with: node scripts/gen-country-paths.cjs
// Generates src/lib/countryPaths.json — SVG path strings per WC team
const topojson = require("topojson-client");
const d3geo = require("d3-geo");
const world = require("world-atlas/countries-110m.json");
const fs = require("fs");
const path = require("path");

const countries = topojson.feature(world, world.objects.countries);

// ISO 3166-1 numeric codes for each WC 2026 team
// England & Scotland both map to GB (826) — best available in 110m
const TEAM_ISO = {
  "United States":         "840",
  "Canada":                "124",
  "Mexico":                "484",
  "Germany":               "276",
  "France":                "250",
  "Spain":                 "724",
  "England":               "826",
  "Scotland":              "826",
  "Portugal":              "620",
  "Netherlands":           "528",
  "Belgium":               "056",
  "Bosnia and Herzegovina":"070",
  "Croatia":               "191",
  "Czechia":               "203",
  "Switzerland":           "756",
  "Austria":               "040",
  "Norway":                "578",
  "Sweden":                "752",
  "Turkey":                "792",
  "Argentina":             "032",
  "Brazil":                "076",
  "Colombia":              "170",
  "Uruguay":               "858",
  "Ecuador":               "218",
  "Paraguay":              "600",
  "Panama":                "591",
  "Haiti":                 "332",
  "Morocco":               "504",
  "Senegal":               "686",
  "Egypt":                 "818",
  "Ghana":                 "288",
  "Côte d'Ivoire":         "384",
  "South Africa":          "710",
  "DR Congo":              "180",
  "Tunisia":               "788",
  "Algeria":               "012",
  "Cape Verde Islands":    "132",
  "Japan":                 "392",
  "Korea Republic":        "410",
  "IR Iran":               "364",
  "Australia":             "036",
  "Saudi Arabia":          "682",
  "Iraq":                  "368",
  "Uzbekistan":            "860",
  "Jordan":                "400",
  "Qatar":                 "634",
  "New Zealand":           "554",
  "Curaçao":               "531",
};

// For countries with overseas territories, use only the largest polygon
// so fitSize doesn't shrink the main landmass to a tiny dot.
function mainLandmass(feat) {
  if (feat.geometry.type !== "MultiPolygon") return feat;
  const largest = feat.geometry.coordinates.reduce((a, b) =>
    b[0].length > a[0].length ? b : a
  );
  return { ...feat, geometry: { type: "Polygon", coordinates: largest } };
}

const W = 400, H = 280;
const result = {};
const missing = [];

for (const [teamName, isoNum] of Object.entries(TEAM_ISO)) {
  const numericId = parseInt(isoNum, 10);
  const feat = countries.features.find(f => Number(f.id) === numericId);

  if (!feat) {
    missing.push(`${teamName} (${isoNum})`);
    continue;
  }

  const main = mainLandmass(feat);
  const proj = d3geo.geoNaturalEarth1().fitSize([W, H], main);
  const pathGen = d3geo.geoPath().projection(proj);
  const d = pathGen(main);
  if (d) result[teamName] = { d, viewBox: `0 0 ${W} ${H}` };
}

if (missing.length) console.warn("⚠ Not found in atlas:", missing.join(", "));

const outPath = path.join(__dirname, "../src/lib/countryPaths.json");
fs.writeFileSync(outPath, JSON.stringify(result, null, 2));
console.log(`✓ Generated ${Object.keys(result).length} country paths → ${outPath}`);

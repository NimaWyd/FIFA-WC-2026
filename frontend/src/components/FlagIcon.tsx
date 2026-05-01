import clsx from "clsx";

// Maps backend canonical team names → ISO 3166-1 alpha-2 codes for flag-icons CSS.
// Includes both canonical and common aliases to handle any name the API returns.
const TEAM_ISO: Record<string, string> = {
  // Hosts
  "United States": "us",
  "Canada": "ca",
  "Mexico": "mx",

  // UEFA
  "Germany": "de",
  "France": "fr",
  "Spain": "es",
  "England": "gb-eng",
  "Portugal": "pt",
  "Netherlands": "nl",
  "Belgium": "be",
  "Bosnia and Herzegovina": "ba",
  "Croatia": "hr",
  "Czechia": "cz",
  "Czech Republic": "cz",        // alias
  "Switzerland": "ch",
  "Austria": "at",
  "Norway": "no",
  "Sweden": "se",
  "Turkey": "tr",
  "Türkiye": "tr",                // alias
  "Scotland": "gb-sct",
  "Wales": "gb-wls",
  "Northern Ireland": "gb-nir",
  "Poland": "pl",
  "Denmark": "dk",
  "Hungary": "hu",
  "Serbia": "rs",
  "Ukraine": "ua",
  "Romania": "ro",
  "Greece": "gr",
  "Slovakia": "sk",
  "Finland": "fi",
  "Iceland": "is",
  "Ireland": "ie",
  "Albania": "al",
  "Slovenia": "si",
  "Montenegro": "me",
  "North Macedonia": "mk",
  "Kosovo": "xk",
  "Bulgaria": "bg",
  "Georgia": "ge",
  "Armenia": "am",
  "Azerbaijan": "az",
  "Belarus": "by",
  "Israel": "il",
  "Russia": "ru",
  "Kazakhstan": "kz",
  "Estonia": "ee",
  "Latvia": "lv",
  "Lithuania": "lt",
  "Luxembourg": "lu",
  "Moldova": "md",
  "Cyprus": "cy",
  "Malta": "mt",
  "Andorra": "ad",
  "Gibraltar": "gi",
  "Faroe Islands": "fo",
  "San Marino": "sm",
  "Liechtenstein": "li",

  // CONMEBOL
  "Argentina": "ar",
  "Brazil": "br",
  "Colombia": "co",
  "Uruguay": "uy",
  "Ecuador": "ec",
  "Paraguay": "py",
  "Venezuela": "ve",
  "Bolivia": "bo",
  "Chile": "cl",
  "Peru": "pe",

  // CONCACAF
  "Panama": "pa",
  "Curaçao": "cw",
  "Haiti": "ht",
  "Costa Rica": "cr",
  "Honduras": "hn",
  "Jamaica": "jm",
  "El Salvador": "sv",
  "Guatemala": "gt",
  "Trinidad and Tobago": "tt",
  "Nicaragua": "ni",

  // CAF
  "Morocco": "ma",
  "Senegal": "sn",
  "Egypt": "eg",
  "Ghana": "gh",
  "Côte d'Ivoire": "ci",
  "Ivory Coast": "ci",            // alias
  "South Africa": "za",
  "DR Congo": "cd",
  "Tunisia": "tn",
  "Algeria": "dz",
  "Cape Verde Islands": "cv",
  "Cape Verde": "cv",             // alias
  "Nigeria": "ng",
  "Cameroon": "cm",
  "Mali": "ml",
  "Burkina Faso": "bf",
  "Guinea": "gn",
  "Benin": "bj",
  "Gabon": "ga",
  "Equatorial Guinea": "gq",
  "Zambia": "zm",
  "Kenya": "ke",
  "Tanzania": "tz",
  "Ethiopia": "et",
  "Angola": "ao",
  "Mozambique": "mz",
  "Zimbabwe": "zw",
  "Uganda": "ug",

  // AFC
  "Japan": "jp",
  "Korea Republic": "kr",
  "South Korea": "kr",            // alias
  "IR Iran": "ir",
  "Iran": "ir",                   // alias
  "Australia": "au",
  "Saudi Arabia": "sa",
  "Iraq": "iq",
  "Uzbekistan": "uz",
  "Jordan": "jo",
  "Qatar": "qa",
  "China": "cn",
  "Kuwait": "kw",
  "Bahrain": "bh",
  "Oman": "om",
  "UAE": "ae",
  "United Arab Emirates": "ae",
  "Syria": "sy",
  "India": "in",
  "Vietnam": "vn",
  "Thailand": "th",
  "Indonesia": "id",
  "Philippines": "ph",
  "Malaysia": "my",
  "Singapore": "sg",

  // OFC
  "New Zealand": "nz",
};

interface Props {
  team: string;
  className?: string;
}

export default function FlagIcon({ team, className }: Props) {
  const iso = TEAM_ISO[team];
  if (!iso) {
    return <span className={clsx("text-slate-500 text-xs", className)}>–</span>;
  }
  // GB subdivisions and Kosovo need special handling
  const SPECIAL: Record<string, string> = {
    "gb-eng": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "gb-sct": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "gb-wls": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "gb-nir": "🇬🇧",
    "xk": "🇽🇰",
  };
  if (iso in SPECIAL) {
    // Fall back to emoji for these — flag-icons CSS also supports them
    // but the class names differ (fi-gb-eng etc.)
    return (
      <span
        className={clsx("fi", `fi-${iso}`, "rounded-sm", className)}
        title={team}
        aria-label={`${team} flag`}
      />
    );
  }
  return (
    <span
      className={clsx("fi", `fi-${iso}`, "rounded-sm", className)}
      title={team}
      aria-label={`${team} flag`}
    />
  );
}

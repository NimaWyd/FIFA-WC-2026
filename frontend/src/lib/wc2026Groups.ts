export type WCMatch = {
  home: string;
  away: string;
  date: string;
  venue: string;
};

export type WCGroup = {
  id: string;
  teams: string[];
  matches: WCMatch[];
};

export const WC2026_GROUPS: WCGroup[] = [
  {
    id: "A",
    teams: ["Mexico", "Korea Republic", "South Africa", "Czechia"],
    matches: [
      { home: "Mexico", away: "South Africa", date: "2026-06-11", venue: "Mexico City" },
      { home: "Korea Republic", away: "Czechia", date: "2026-06-12", venue: "Guadalajara" },
      { home: "Mexico", away: "Korea Republic", date: "2026-06-18", venue: "Guadalajara" },
      { home: "Czechia", away: "South Africa", date: "2026-06-18", venue: "Atlanta" },
      { home: "Czechia", away: "Mexico", date: "2026-06-25", venue: "Mexico City" },
      { home: "South Africa", away: "Korea Republic", date: "2026-06-25", venue: "Monterrey" },
    ],
  },
  {
    id: "B",
    teams: ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    matches: [
      { home: "Canada", away: "Bosnia and Herzegovina", date: "2026-06-12", venue: "Toronto" },
      { home: "Qatar", away: "Switzerland", date: "2026-06-13", venue: "San Francisco" },
      { home: "Switzerland", away: "Bosnia and Herzegovina", date: "2026-06-18", venue: "Los Angeles" },
      { home: "Canada", away: "Qatar", date: "2026-06-18", venue: "Vancouver" },
      { home: "Switzerland", away: "Canada", date: "2026-06-24", venue: "Vancouver" },
      { home: "Bosnia and Herzegovina", away: "Qatar", date: "2026-06-24", venue: "Seattle" },
    ],
  },
  {
    id: "C",
    teams: ["Brazil", "Morocco", "Scotland", "Haiti"],
    matches: [
      { home: "Brazil", away: "Morocco", date: "2026-06-13", venue: "New York/New Jersey" },
      { home: "Haiti", away: "Scotland", date: "2026-06-13", venue: "Boston" },
      { home: "Scotland", away: "Morocco", date: "2026-06-19", venue: "Boston" },
      { home: "Brazil", away: "Haiti", date: "2026-06-19", venue: "Philadelphia" },
      { home: "Morocco", away: "Haiti", date: "2026-06-24", venue: "Atlanta" },
      { home: "Scotland", away: "Brazil", date: "2026-06-24", venue: "Miami" },
    ],
  },
  {
    id: "D",
    teams: ["United States", "Paraguay", "Australia", "Turkey"],
    matches: [
      { home: "United States", away: "Paraguay", date: "2026-06-12", venue: "Los Angeles" },
      { home: "Australia", away: "Turkey", date: "2026-06-14", venue: "Vancouver" },
      { home: "United States", away: "Australia", date: "2026-06-19", venue: "Seattle" },
      { home: "Turkey", away: "Paraguay", date: "2026-06-19", venue: "San Francisco" },
      { home: "Turkey", away: "United States", date: "2026-06-25", venue: "Los Angeles" },
      { home: "Paraguay", away: "Australia", date: "2026-06-25", venue: "San Francisco" },
    ],
  },
  {
    id: "E",
    teams: ["Germany", "Côte d'Ivoire", "Ecuador", "Curaçao"],
    matches: [
      { home: "Germany", away: "Curaçao", date: "2026-06-14", venue: "Houston" },
      { home: "Côte d'Ivoire", away: "Ecuador", date: "2026-06-14", venue: "Philadelphia" },
      { home: "Germany", away: "Côte d'Ivoire", date: "2026-06-20", venue: "Toronto" },
      { home: "Ecuador", away: "Curaçao", date: "2026-06-20", venue: "Kansas City" },
      { home: "Ecuador", away: "Germany", date: "2026-06-25", venue: "New York/New Jersey" },
      { home: "Curaçao", away: "Côte d'Ivoire", date: "2026-06-25", venue: "Philadelphia" },
    ],
  },
  {
    id: "F",
    teams: ["Netherlands", "Japan", "Sweden", "Tunisia"],
    matches: [
      { home: "Netherlands", away: "Japan", date: "2026-06-14", venue: "Dallas" },
      { home: "Sweden", away: "Tunisia", date: "2026-06-14", venue: "Monterrey" },
      { home: "Netherlands", away: "Sweden", date: "2026-06-20", venue: "Houston" },
      { home: "Tunisia", away: "Japan", date: "2026-06-20", venue: "Monterrey" },
      { home: "Tunisia", away: "Netherlands", date: "2026-06-25", venue: "Kansas City" },
      { home: "Japan", away: "Sweden", date: "2026-06-25", venue: "Dallas" },
    ],
  },
  {
    id: "G",
    teams: ["Belgium", "Egypt", "IR Iran", "New Zealand"],
    matches: [
      { home: "Belgium", away: "Egypt", date: "2026-06-15", venue: "Seattle" },
      { home: "IR Iran", away: "New Zealand", date: "2026-06-15", venue: "Los Angeles" },
      { home: "Belgium", away: "IR Iran", date: "2026-06-21", venue: "Los Angeles" },
      { home: "New Zealand", away: "Egypt", date: "2026-06-21", venue: "Vancouver" },
      { home: "New Zealand", away: "Belgium", date: "2026-06-26", venue: "Vancouver" },
      { home: "Egypt", away: "IR Iran", date: "2026-06-26", venue: "Seattle" },
    ],
  },
  {
    id: "H",
    teams: ["Spain", "Saudi Arabia", "Uruguay", "Cape Verde Islands"],
    matches: [
      { home: "Spain", away: "Cape Verde Islands", date: "2026-06-15", venue: "Atlanta" },
      { home: "Saudi Arabia", away: "Uruguay", date: "2026-06-15", venue: "Miami" },
      { home: "Spain", away: "Saudi Arabia", date: "2026-06-21", venue: "Atlanta" },
      { home: "Uruguay", away: "Cape Verde Islands", date: "2026-06-21", venue: "Miami" },
      { home: "Uruguay", away: "Spain", date: "2026-06-26", venue: "Guadalajara" },
      { home: "Cape Verde Islands", away: "Saudi Arabia", date: "2026-06-26", venue: "Houston" },
    ],
  },
  {
    id: "I",
    teams: ["France", "Senegal", "Norway", "Iraq"],
    matches: [
      { home: "France", away: "Senegal", date: "2026-06-16", venue: "New York/New Jersey" },
      { home: "Iraq", away: "Norway", date: "2026-06-16", venue: "Boston" },
      { home: "France", away: "Iraq", date: "2026-06-22", venue: "Philadelphia" },
      { home: "Norway", away: "Senegal", date: "2026-06-22", venue: "New York/New Jersey" },
      { home: "Norway", away: "France", date: "2026-06-26", venue: "Boston" },
      { home: "Senegal", away: "Iraq", date: "2026-06-26", venue: "Toronto" },
    ],
  },
  {
    id: "J",
    teams: ["Argentina", "Algeria", "Austria", "Jordan"],
    matches: [
      { home: "Argentina", away: "Algeria", date: "2026-06-16", venue: "Kansas City" },
      { home: "Austria", away: "Jordan", date: "2026-06-16", venue: "San Francisco" },
      { home: "Argentina", away: "Austria", date: "2026-06-22", venue: "Dallas" },
      { home: "Jordan", away: "Algeria", date: "2026-06-22", venue: "San Francisco" },
      { home: "Jordan", away: "Argentina", date: "2026-06-27", venue: "Dallas" },
      { home: "Algeria", away: "Austria", date: "2026-06-27", venue: "Kansas City" },
    ],
  },
  {
    id: "K",
    teams: ["Portugal", "Uzbekistan", "Colombia", "DR Congo"],
    matches: [
      { home: "Portugal", away: "DR Congo", date: "2026-06-17", venue: "Houston" },
      { home: "Uzbekistan", away: "Colombia", date: "2026-06-17", venue: "Mexico City" },
      { home: "Portugal", away: "Uzbekistan", date: "2026-06-23", venue: "Houston" },
      { home: "Colombia", away: "DR Congo", date: "2026-06-23", venue: "Guadalajara" },
      { home: "Colombia", away: "Portugal", date: "2026-06-27", venue: "Miami" },
      { home: "DR Congo", away: "Uzbekistan", date: "2026-06-27", venue: "Atlanta" },
    ],
  },
  {
    id: "L",
    teams: ["England", "Croatia", "Ghana", "Panama"],
    matches: [
      { home: "England", away: "Croatia", date: "2026-06-17", venue: "Dallas" },
      { home: "Ghana", away: "Panama", date: "2026-06-17", venue: "Toronto" },
      { home: "England", away: "Ghana", date: "2026-06-23", venue: "Boston" },
      { home: "Panama", away: "Croatia", date: "2026-06-23", venue: "Toronto" },
      { home: "Panama", away: "England", date: "2026-06-27", venue: "New York/New Jersey" },
      { home: "Croatia", away: "Ghana", date: "2026-06-27", venue: "Philadelphia" },
    ],
  },
];

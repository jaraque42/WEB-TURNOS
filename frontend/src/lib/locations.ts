export const LOCATION_CATALOG = {
  T123: ['B25', 'D63', 'M5', 'M1', 'S1', 'S2', 'S6', 'PISTA'],
  T4: ['M13', 'J49', 'J49P', 'ZM', 'K98', 'PISTA'],
  T4S: ['S27', 'M40', 'CN', 'PISTA'],
} as const;

export type LocationTerminal = keyof typeof LOCATION_CATALOG;

export interface LocationOption {
  value: string;
  terminal: LocationTerminal;
  subcategory: string;
  label: string;
}

export function toLocationValue(terminal: LocationTerminal, subcategory: string): string {
  return `${terminal}:${subcategory}`;
}

export function parseLocationValue(location: string): { terminal: LocationTerminal; subcategory: string } | null {
  const [terminal, subcategory] = location.split(':');
  if (!terminal || !subcategory) return null;
  if (!(terminal in LOCATION_CATALOG)) return null;
  return { terminal: terminal as LocationTerminal, subcategory };
}

export const LOCATION_OPTIONS: LocationOption[] = (Object.entries(LOCATION_CATALOG) as [LocationTerminal, readonly string[]][])
  .flatMap(([terminal, subcategories]) =>
    subcategories.map((subcategory) => ({
      value: toLocationValue(terminal, subcategory),
      terminal,
      subcategory,
      label: `${terminal} · ${subcategory}`,
    }))
  );

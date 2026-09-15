// Mirrors the CSS custom properties in src/styles/theme.css's :root block.
// Motion (motion/react) needs literal values, not CSS var() references, so
// these are kept in sync by hand — if you change theme.css's --ease-* values,
// update these too.
export const EASE_STANDARD = [0.4, 0, 0.2, 1] as const;
export const EASE_OUT = [0.23, 1, 0.32, 1] as const;

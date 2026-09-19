import {loadFont} from '@remotion/google-fonts/Poppins';

export const COLORS = {
	primaryTeal: '#0F766E',
	accentGreen: '#22C55E',
	secondaryOrange: '#F59E0B',
	lightBg: '#F7F7F8',
	darkBg: '#0B0F0E',
	white: '#FFFFFF',
	textOnLight: '#0B0F0E',
	textOnDark: '#F7F7F8',
	textMuted: '#6B7280',
	cardBorder: 'rgba(11, 15, 14, 0.08)',
	shadowColor: 'rgba(11, 15, 14, 0.18)',
} as const;

const {fontFamily} = loadFont('normal', {weights: ['500'], subsets: ['latin']});

export const FONT_FAMILY = fontFamily;
export const FONT_WEIGHT_MEDIUM = 500;

export const SAFE_MARGIN = 120;

import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';

interface Props {
	targetValue: number;
	suffix?: string;
	prefix?: string;
	label: string;
	startFrame: number;
	durationInFrames?: number;
	accentColor?: string;
	dark?: boolean;
	decimals?: number;
	size?: 'large' | 'small';
}

export const MetricCounter: React.FC<Props> = ({
	targetValue,
	suffix = '',
	prefix = '',
	label,
	startFrame,
	durationInFrames = 36,
	accentColor = COLORS.accentGreen,
	dark = true,
	decimals = 0,
	size = 'large',
}) => {
	const numberFontSize = size === 'large' ? 88 : 40;
	const labelFontSize = size === 'large' ? 24 : 15;
	const labelMaxWidth = size === 'large' ? 260 : 160;
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const local = frame - startFrame;

	const raw = interpolate(local, [0, durationInFrames], [0, targetValue], {
		easing: Easing.out(Easing.cubic),
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const factor = 10 ** decimals;
	const value = Math.round(raw * factor) / factor;

	const cardSpring = spring({frame: local, fps, config: {damping: 200, stiffness: 120, mass: 0.9}});
	const cardOpacity = interpolate(local, [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const cardY = interpolate(cardSpring, [0, 1], [20, 0]);

	const labelSpring = spring({
		frame: local - durationInFrames + 6,
		fps,
		config: {damping: 200, stiffness: 120, mass: 0.9},
	});
	const labelOpacity = interpolate(local, [durationInFrames - 6, durationInFrames + 6], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const labelY = interpolate(labelSpring, [0, 1], [10, 0]);

	return (
		<div
			style={{
				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
				opacity: cardOpacity,
				transform: `translateY(${cardY}px)`,
			}}
		>
			<div
				style={{
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: numberFontSize,
					color: accentColor,
					lineHeight: 1,
				}}
			>
				{prefix}
				{value.toLocaleString(undefined, {
					minimumFractionDigits: decimals,
					maximumFractionDigits: decimals,
				})}
				{suffix}
			</div>
			<div
				style={{
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: labelFontSize,
					color: dark ? COLORS.textOnDark : COLORS.textOnLight,
					marginTop: size === 'large' ? 14 : 6,
					opacity: labelOpacity,
					transform: `translateY(${labelY}px)`,
					textAlign: 'center',
					maxWidth: labelMaxWidth,
				}}
			>
				{label}
			</div>
		</div>
	);
};

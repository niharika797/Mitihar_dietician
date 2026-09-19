import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';

interface Props {
	headline: string;
	supporting?: string;
	startFrame: number;
	align?: 'left' | 'center';
	dark?: boolean;
	accentColor?: string;
	/** Use a smaller scale when a screenshot/device mockup sits close below the title. */
	compact?: boolean;
}

export const SectionTitle: React.FC<Props> = ({
	headline,
	supporting,
	startFrame,
	align = 'left',
	dark = false,
	accentColor = COLORS.accentGreen,
	compact = false,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const local = frame - startFrame;

	const headlineSpring = spring({
		frame: local,
		fps,
		config: {damping: 200, stiffness: 120, mass: 0.9},
	});
	const headlineY = interpolate(headlineSpring, [0, 1], [24, 0]);
	const headlineOpacity = interpolate(local, [0, 15], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	const supportSpring = spring({
		frame: local - 10,
		fps,
		config: {damping: 200, stiffness: 120, mass: 0.9},
	});
	const supportY = interpolate(supportSpring, [0, 1], [16, 0]);
	const supportOpacity = interpolate(local, [10, 25], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	return (
		<div
			style={{
				display: 'flex',
				flexDirection: 'column',
				alignItems: align === 'center' ? 'center' : 'flex-start',
				textAlign: align,
			}}
		>
			<div
				style={{
					width: compact ? 48 : 64,
					height: compact ? 5 : 6,
					borderRadius: 3,
					backgroundColor: accentColor,
					marginBottom: compact ? 16 : 28,
					opacity: headlineOpacity,
					transform: `translateY(${headlineY}px)`,
				}}
			/>
			<h1
				style={{
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: compact ? 42 : 64,
					lineHeight: 1.15,
					color: dark ? COLORS.textOnDark : COLORS.textOnLight,
					margin: 0,
					opacity: headlineOpacity,
					transform: `translateY(${headlineY}px)`,
					maxWidth: compact ? 1500 : 1200,
					whiteSpace: compact ? 'nowrap' : undefined,
				}}
			>
				{headline}
			</h1>
			{supporting ? (
				<p
					style={{
						fontFamily: FONT_FAMILY,
						fontWeight: 500,
						fontSize: compact ? 20 : 30,
						lineHeight: 1.4,
						color: dark ? COLORS.textOnDark : COLORS.textMuted,
						marginTop: compact ? 10 : 20,
						opacity: supportOpacity,
						transform: `translateY(${supportY}px)`,
						maxWidth: compact ? 1500 : 900,
						whiteSpace: compact ? 'nowrap' : undefined,
					}}
				>
					{supporting}
				</p>
			) : null}
		</div>
	);
};

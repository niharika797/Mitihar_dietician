import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';
import {SectionTitle} from '../components/SectionTitle';

const OBJECTIVES = [
	'Automate personalized clinical meal-plan generation.',
	'Keep doctors and dietitians in control through review and approval.',
	'Make dietary plans easier to follow in everyday life.',
	'Connect planning with patient behavior and progress.',
	'Streamline clinic operations through a connected platform.',
];

const ObjectiveRow: React.FC<{text: string; index: number; startFrame: number}> = ({text, index, startFrame}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const local = frame - startFrame;
	const s = spring({frame: local, fps, config: {damping: 200, stiffness: 120, mass: 0.9}});
	const x = interpolate(s, [0, 1], [-40, 0]);
	const opacity = interpolate(local, [0, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

	return (
		<div
			style={{
				display: 'flex',
				alignItems: 'center',
				gap: 28,
				opacity,
				transform: `translateX(${x}px)`,
				marginBottom: 34,
			}}
		>
			<div
				style={{
					width: 56,
					height: 56,
					borderRadius: 28,
					backgroundColor: COLORS.primaryTeal,
					color: COLORS.white,
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: 24,
					flexShrink: 0,
				}}
			>
				{index + 1}
			</div>
			<div
				style={{
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: 32,
					color: COLORS.textOnLight,
					maxWidth: 1200,
				}}
			>
				{text}
			</div>
		</div>
	);
};

export const Scene11Objectives: React.FC = () => {
	return (
		<AbsoluteFill style={{backgroundColor: COLORS.lightBg}}>
			<div style={{position: 'absolute', top: 90, left: 120}}>
				<SectionTitle headline="What Mitihar is built to do." startFrame={0} />
			</div>
			<div style={{position: 'absolute', top: 320, left: 120}}>
				{OBJECTIVES.map((text, i) => (
					<ObjectiveRow key={text} text={text} index={i} startFrame={40 + i * 30} />
				))}
			</div>
		</AbsoluteFill>
	);
};

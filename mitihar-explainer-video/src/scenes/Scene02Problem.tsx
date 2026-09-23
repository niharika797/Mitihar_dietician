import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';
import {SectionTitle} from '../components/SectionTitle';

interface ProblemCard {
	emoji: string;
	title: string;
	subtitle: string;
	x: number;
	y: number;
	startFrame: number;
}

const CARDS: ProblemCard[] = [
	{emoji: '📊', title: 'Spreadsheet', subtitle: 'manual BMR & TDEE math', x: 260, y: 560, startFrame: 55},
	{emoji: '📄', title: 'Static PDF', subtitle: 'one-time meal chart', x: 700, y: 700, startFrame: 85},
	{emoji: '💬', title: 'Chat thread', subtitle: '"what should I eat today?"', x: 1180, y: 560, startFrame: 115},
	{emoji: '❔', title: 'No visibility', subtitle: 'did the patient even follow it?', x: 1600, y: 700, startFrame: 145},
];

const Card: React.FC<ProblemCard & {collapseFrame: number}> = ({
	emoji,
	title,
	subtitle,
	x,
	y,
	startFrame,
	collapseFrame,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const local = frame - startFrame;

	const popSpring = spring({frame: local, fps, config: {damping: 13, stiffness: 140, mass: 0.8}});
	const scale = interpolate(popSpring, [0, 1], [0.7, 1]);
	const opacity = interpolate(local, [0, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

	const collapseLocal = frame - collapseFrame;
	const collapseProgress = interpolate(collapseLocal, [0, 40], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const centerX = 960;
	const centerY = 620;
	const cx = interpolate(collapseProgress, [0, 1], [x, centerX]);
	const cy = interpolate(collapseProgress, [0, 1], [y, centerY]);
	const collapseOpacity = interpolate(collapseProgress, [0, 1], [1, 0]);

	return (
		<div
			style={{
				position: 'absolute',
				left: cx,
				top: cy,
				transform: `translate(-50%, -50%) scale(${scale})`,
				opacity: opacity * collapseOpacity,
				backgroundColor: COLORS.white,
				borderRadius: 20,
				padding: '28px 32px',
				boxShadow: `0 30px 60px -20px ${COLORS.shadowColor}`,
				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
				width: 280,
			}}
		>
			<div style={{fontSize: 48}}>{emoji}</div>
			<div style={{fontFamily: FONT_FAMILY, fontWeight: 500, fontSize: 24, color: COLORS.textOnLight, marginTop: 10}}>
				{title}
			</div>
			<div
				style={{
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: 16,
					color: COLORS.textMuted,
					marginTop: 6,
					textAlign: 'center',
				}}
			>
				{subtitle}
			</div>
		</div>
	);
};

export const Scene02Problem: React.FC = () => {
	const frame = useCurrentFrame();
	const collapseFrame = 520;
	const closingOpacity = interpolate(frame, [collapseFrame + 30, collapseFrame + 55], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill
			style={{
				backgroundColor: COLORS.lightBg,
				translate: '1px 0px'
			}}
			from={-38}
		>
			<div style={{position: 'absolute', top: 120, left: 120}}>
				<SectionTitle
					headline="Too much manual work."
					supporting="Between the clinic visit and the next meal, the plan gets lost."
					startFrame={0}
				/>
			</div>
			{CARDS.map((c) => (
				<Card key={c.title} {...c} collapseFrame={collapseFrame} />
			))}
			<div
				style={{
					position: 'absolute',
					top: 0,
					left: 0,
					width: '100%',
					height: '100%',
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					opacity: closingOpacity,
				}}
			>
				<div
					style={{
						fontFamily: FONT_FAMILY,
						fontWeight: 500,
						fontSize: 56,
						color: COLORS.textOnLight,
						textAlign: 'center',
						lineHeight: 1.3,
					}}
				>
					Too much manual work.
					<br />
					<span style={{color: COLORS.primaryTeal}}>Too little visibility.</span>
				</div>
			</div>
		</AbsoluteFill>
	);
};

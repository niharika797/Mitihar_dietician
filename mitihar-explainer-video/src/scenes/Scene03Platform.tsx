import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';
import {SectionTitle} from '../components/SectionTitle';

interface Node {
	label: string;
	sub: string;
	emoji: string;
	x: number;
	y: number;
	startFrame: number;
}

const NODES: Node[] = [
	{label: 'Doctor Dashboard', sub: 'review & approve', emoji: '💻', x: 500, y: 640, startFrame: 60},
	{label: 'Patient App', sub: 'daily plan & tracking', emoji: '📱', x: 1420, y: 640, startFrame: 90},
	{label: 'Core Platform', sub: 'plans, recipes, records', emoji: '🗄️', x: 960, y: 880, startFrame: 120},
];

const NodeCircle: React.FC<Node> = ({label, sub, emoji, x, y, startFrame}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const local = frame - startFrame;
	const s = spring({frame: local, fps, config: {damping: 13, stiffness: 140, mass: 0.8}});
	const scale = interpolate(s, [0, 1], [0.6, 1]);
	const opacity = interpolate(local, [0, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

	return (
		<div
			style={{
				position: 'absolute',
				left: x,
				top: y,
				transform: `translate(-50%, -50%) scale(${scale})`,
				opacity,
				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
			}}
		>
			<div
				style={{
					width: 160,
					height: 160,
					borderRadius: 80,
					backgroundColor: COLORS.white,
					boxShadow: `0 30px 60px -20px ${COLORS.shadowColor}`,
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					fontSize: 64,
					border: `3px solid ${COLORS.primaryTeal}`,
				}}
			>
				{emoji}
			</div>
			<div style={{fontFamily: FONT_FAMILY, fontWeight: 500, fontSize: 26, color: COLORS.textOnLight, marginTop: 18}}>
				{label}
			</div>
			<div style={{fontFamily: FONT_FAMILY, fontWeight: 500, fontSize: 17, color: COLORS.textMuted, marginTop: 4}}>
				{sub}
			</div>
		</div>
	);
};

const Connector: React.FC<{x1: number; y1: number; x2: number; y2: number; startFrame: number}> = ({
	x1,
	y1,
	x2,
	y2,
	startFrame,
}) => {
	const frame = useCurrentFrame();
	const local = frame - startFrame;
	const progress = interpolate(local, [0, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const cx = interpolate(progress, [0, 1], [x1, x2]);
	const cy = interpolate(progress, [0, 1], [y1, y2]);
	const opacity = interpolate(local, [0, 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

	return (
		<svg width="100%" height="100%" style={{position: 'absolute', top: 0, left: 0}}>
			<line x1={x1} y1={y1} x2={cx} y2={cy} stroke={COLORS.accentGreen} strokeWidth={4} opacity={opacity} />
		</svg>
	);
};

export const Scene03Platform: React.FC = () => {
	return (
		<AbsoluteFill style={{backgroundColor: COLORS.lightBg}}>
			<div style={{position: 'absolute', top: 100, left: 120}}>
				<SectionTitle
					headline="Mitihar connects three layers around one clinical plan."
					supporting="A doctor dashboard, a patient app, and the platform that keeps them in sync."
					startFrame={0}
				/>
			</div>
			<Connector x1={500} y1={640} x2={960} y2={880} startFrame={150} />
			<Connector x1={1420} y1={640} x2={960} y2={880} startFrame={170} />
			<Connector x1={500} y1={640} x2={1420} y2={640} startFrame={190} />
			{NODES.map((n) => (
				<NodeCircle key={n.label} {...n} />
			))}
		</AbsoluteFill>
	);
};

import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';

interface Props {
	text: string;
	startFrame: number;
	x: number;
	y: number;
	accentColor?: string;
	leaderTo?: {x: number; y: number};
}

export const FeatureCallout: React.FC<Props> = ({
	text,
	startFrame,
	x,
	y,
	accentColor = COLORS.primaryTeal,
	leaderTo,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const local = frame - startFrame;

	const popSpring = spring({frame: local, fps, config: {damping: 14, stiffness: 160, mass: 0.7}});
	const scale = interpolate(popSpring, [0, 1], [0.9, 1]);
	const opacity = interpolate(local, [0, 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

	const leaderProgress = interpolate(local, [0, 16], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	return (
		<>
			{leaderTo ? (
				<svg
					width="100%"
					height="100%"
					style={{position: 'absolute', top: 0, left: 0, pointerEvents: 'none'}}
				>
					<line
						x1={x}
						y1={y}
						x2={x + (leaderTo.x - x) * leaderProgress}
						y2={y + (leaderTo.y - y) * leaderProgress}
						stroke={accentColor}
						strokeWidth={3}
						strokeDasharray="6 6"
						opacity={opacity}
					/>
				</svg>
			) : null}
			<div
				style={{
					position: 'absolute',
					left: x,
					top: y,
					transform: `scale(${scale})`,
					opacity,
					backgroundColor: accentColor,
					color: COLORS.white,
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: 22,
					padding: '12px 22px',
					borderRadius: 999,
					boxShadow: `0 12px 30px -8px ${COLORS.shadowColor}`,
					whiteSpace: 'nowrap',
				}}
			>
				{text}
			</div>
		</>
	);
};

import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS} from '../constants/brand';

export interface Waypoint {
	frame: number;
	x: number;
	y: number;
}

interface Props {
	waypoints: Waypoint[];
	clickFrames?: number[];
}

export const Cursor: React.FC<Props> = ({waypoints, clickFrames = []}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	let x = waypoints[0]?.x ?? 0;
	let y = waypoints[0]?.y ?? 0;

	for (let i = 0; i < waypoints.length - 1; i++) {
		const a = waypoints[i];
		const b = waypoints[i + 1];
		if (frame >= a.frame && frame <= b.frame) {
			const segProgress = spring({
				frame: frame - a.frame,
				fps,
				config: {damping: 200, stiffness: 90, mass: 1},
				durationInFrames: Math.max(b.frame - a.frame, 1),
			});
			x = interpolate(segProgress, [0, 1], [a.x, b.x]);
			y = interpolate(segProgress, [0, 1], [a.y, b.y]);
		} else if (frame > b.frame) {
			x = b.x;
			y = b.y;
		}
	}

	return (
		<div style={{position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none'}}>
			{clickFrames.map((clickFrame) => {
				const local = frame - clickFrame;
				if (local < 0 || local > 18) return null;
				const scale = interpolate(local, [0, 18], [0, 1.6], {extrapolateRight: 'clamp'});
				const opacity = interpolate(local, [0, 18], [0.6, 0], {extrapolateRight: 'clamp'});
				return (
					<div
						key={clickFrame}
						style={{
							position: 'absolute',
							left: x - 20,
							top: y - 20,
							width: 40,
							height: 40,
							borderRadius: 20,
							backgroundColor: COLORS.accentGreen,
							transform: `scale(${scale})`,
							opacity,
						}}
					/>
				);
			})}
			<div
				style={{
					position: 'absolute',
					left: x,
					top: y,
					width: 0,
					height: 0,
					filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.35))',
				}}
			>
				<svg width={28} height={28} viewBox="0 0 28 28">
					<path
						d="M4 2 L4 22 L9.5 17.5 L13 25 L16.5 23.5 L13 16 L20 16 Z"
						fill="#FFFFFF"
						stroke="#0B0F0E"
						strokeWidth={1.5}
					/>
				</svg>
			</div>
		</div>
	);
};

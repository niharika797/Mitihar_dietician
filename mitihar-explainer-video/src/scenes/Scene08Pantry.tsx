import React from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {COLORS} from '../constants/brand';
import {SectionTitle} from '../components/SectionTitle';
import {DeviceFrame} from '../components/DeviceFrame';
import {ScreenshotReveal} from '../components/ScreenshotReveal';
import {FeatureCallout} from '../components/FeatureCallout';

const DW = 340;
const DH = 736;
const DEVICE_TOP = 260;

interface Phase {
	src: string;
	from: number;
	to: number;
}

const PHASES: Phase[] = [
	{src: staticFile('screenshots/captured/mobile-pantry-fresh.png'), from: 40, to: 320},
	{src: staticFile('screenshots/captured/mobile-shopping-list-fresh.png'), from: 300, to: 600},
];

const PhaseLayer: React.FC<Phase> = ({src, from, to}) => {
	const frame = useCurrentFrame();
	const fadeDur = 18;
	const opacity = interpolate(frame, [from, from + fadeDur, to - fadeDur, to], [0, 1, 1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	if (opacity <= 0) return null;
	return (
		<div style={{position: 'absolute', top: 0, left: 0, width: DW, height: DH, opacity}}>
			<ScreenshotReveal src={src} width={DW} height={DH} startFrame={from} revealDurationInFrames={1} />
		</div>
	);
};

export const Scene08Pantry: React.FC = () => {
	return (
		<AbsoluteFill style={{backgroundColor: COLORS.lightBg, alignItems: 'center'}}>
			<div style={{position: 'absolute', top: 90, left: 120}}>
				<SectionTitle
					headline="From plan to pantry."
					supporting="A generated shopping list and pantry view, right on the home screen."
					startFrame={0}
					compact
				/>
			</div>
			<div style={{position: 'absolute', top: DEVICE_TOP, left: '50%', transform: 'translateX(-50%)'}}>
				<DeviceFrame width={DW} height={DH}>
					{PHASES.map((p) => (
						<PhaseLayer key={p.src} {...p} />
					))}
					<FeatureCallout text="Ingredients already on hand" startFrame={100} x={36} y={465} />
					<FeatureCallout text="Auto-generated shopping list" startFrame={360} x={36} y={519} />
				</DeviceFrame>
			</div>
		</AbsoluteFill>
	);
};

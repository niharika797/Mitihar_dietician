import React from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {COLORS} from '../constants/brand';
import {SectionTitle} from '../components/SectionTitle';
import {DeviceFrame} from '../components/DeviceFrame';
import {ScreenshotReveal} from '../components/ScreenshotReveal';
import {Cursor} from '../components/Cursor';

const DW = 340;
const DH = 736; // matches captured 414x896 aspect
const DEVICE_TOP = 260;

interface Phase {
	src: string;
	from: number;
	to: number;
	cropBottomPx?: number;
}

const PHASES: Phase[] = [
	{src: staticFile('screenshots/existing/03-onboarding-personal-info.png'), from: 30, to: 190},
	{src: staticFile('screenshots/existing/04-activity-level.png'), from: 170, to: 330},
	{src: staticFile('screenshots/existing/05-disclaimer.png'), from: 310, to: 470},
	{src: staticFile('screenshots/captured/mobile-home-fresh.png'), from: 450, to: 660},
	{src: staticFile('screenshots/existing/patient-02-meals-tab.png'), from: 640, to: 850},
	{src: staticFile('screenshots/captured/mobile-progress-fresh.png'), from: 830, to: 1050, cropBottomPx: 90},
];

const PhaseLayer: React.FC<Phase> = ({src, from, to, cropBottomPx}) => {
	const frame = useCurrentFrame();
	const fadeDur = 16;
	const opacity = interpolate(frame, [from, from + fadeDur, to - fadeDur, to], [0, 1, 1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	if (opacity <= 0) return null;
	return (
		<div style={{position: 'absolute', top: 0, left: 0, width: DW, height: DH, opacity}}>
			<ScreenshotReveal
				src={src}
				width={DW}
				height={DH}
				startFrame={from}
				revealDurationInFrames={1}
				cropBottomPx={cropBottomPx}
				naturalHeightPx={cropBottomPx ? 896 : undefined}
			/>
		</div>
	);
};

export const Scene07PatientApp: React.FC = () => {
	return (
		<AbsoluteFill style={{backgroundColor: COLORS.lightBg, alignItems: 'center'}}>
			<div style={{position: 'absolute', top: 90, left: 120}}>
				<SectionTitle
					headline="The plan follows the patient home."
					supporting="Onboarding, daily meals, logging, and progress — in one connected app."
					startFrame={0}
					compact
				/>
			</div>
			<div style={{position: 'absolute', top: DEVICE_TOP, left: '50%', transform: 'translateX(-50%)'}}>
				<DeviceFrame width={DW} height={DH}>
					{PHASES.map((p) => (
						<PhaseLayer key={p.src} {...p} />
					))}
					<Cursor waypoints={[{frame: 660, x: 170, y: 447}]} clickFrames={[665]} />
				</DeviceFrame>
			</div>
		</AbsoluteFill>
	);
};

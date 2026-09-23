import React from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {COLORS} from '../constants/brand';
import {SectionTitle} from '../components/SectionTitle';
import {BrowserFrame} from '../components/BrowserFrame';
import {ScreenshotReveal} from '../components/ScreenshotReveal';
import {FeatureCallout} from '../components/FeatureCallout';
import {Cursor} from '../components/Cursor';

const BW = 1300;
const BH = 731; // 16:9 crop of the 1920x1080 capture
const FRAME_TOP = 260;

interface Phase {
	src: string;
	from: number;
	to: number;
}

const PHASES: Phase[] = [
	{src: staticFile('screenshots/captured/doctor-overview-fresh.png'), from: 40, to: 380},
	{src: staticFile('screenshots/captured/doctor-patient-list-fresh.png'), from: 350, to: 680},
	{src: staticFile('screenshots/captured/doctor-patient-profile-bmr.png'), from: 650, to: 990},
];

const PhaseLayer: React.FC<Phase & {index: number}> = ({src, from, to, index}) => {
	const frame = useCurrentFrame();
	const fadeDur = 20;
	const opacity = interpolate(
		frame,
		[from, from + fadeDur, to - fadeDur, to],
		[0, 1, 1, 0],
		{extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
	);
	if (opacity <= 0) return null;

	return (
		<div style={{position: 'absolute', top: 0, left: 0, width: BW, height: BH, opacity}}>
			<ScreenshotReveal
				src={src}
				width={BW}
				height={BH}
				startFrame={from}
				revealDurationInFrames={index === 0 ? 24 : 1}
				kenBurns={{fromScale: 1, toScale: 1.08}}
			/>
		</div>
	);
};

export const Scene04DoctorDashboard: React.FC = () => {
	return (
		<AbsoluteFill
			style={{
				backgroundColor: COLORS.lightBg,
				alignItems: 'center'
			}}
		>
			<div style={{position: 'absolute', top: 90, left: 120}}>
				<SectionTitle
					headline="One dashboard for every patient's plan."
					supporting="Overview, patient roster, and full clinical detail in one workspace."
					startFrame={0}
					compact
				/>
			</div>
			<div style={{position: 'absolute', top: FRAME_TOP, left: '50%', transform: 'translateX(-50%)'}}>
				<BrowserFrame width={BW} height={BH} label="Doctor Dashboard">
					{PHASES.map((p, i) => (
						<PhaseLayer key={p.src} {...p} index={i} />
					))}
					<FeatureCallout text="12 Active Patients" startFrame={90} x={80} y={180} />
					<Cursor
						waypoints={[
							{frame: 380, x: 433, y: 364},
							{frame: 470, x: 433, y: 407},
							{frame: 560, x: 676, y: 416},
						]}
						clickFrames={[570]}
					/>
					<FeatureCallout text="Open patient profile" startFrame={660} x={780} y={78} />
				</BrowserFrame>
			</div>
		</AbsoluteFill>
	);
};

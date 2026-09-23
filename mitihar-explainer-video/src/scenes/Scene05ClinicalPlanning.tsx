import React from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {COLORS} from '../constants/brand';
import {SectionTitle} from '../components/SectionTitle';
import {BrowserFrame} from '../components/BrowserFrame';
import {ScreenshotReveal} from '../components/ScreenshotReveal';
import {FeatureCallout} from '../components/FeatureCallout';
import {MetricCounter} from '../components/MetricCounter';

const BW = 1300;
const BH = 731;
const FRAME_TOP = 260;

interface Phase {
	src: string;
	from: number;
	to: number;
}

const PHASES: Phase[] = [
	{src: staticFile('screenshots/captured/doctor-patient-profile-bmr.png'), from: 40, to: 340},
	{src: staticFile('screenshots/captured/doctor-plan-tab-testpatient.png'), from: 310, to: 620},
	{src: staticFile('screenshots/captured/doctor-meal-config-fresh.png'), from: 590, to: 900},
];

const PhaseLayer: React.FC<Phase> = ({src, from, to}) => {
	const frame = useCurrentFrame();
	const fadeDur = 20;
	const opacity = interpolate(frame, [from, from + fadeDur, to - fadeDur, to], [0, 1, 1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	if (opacity <= 0) return null;
	return (
		<div style={{position: 'absolute', top: 0, left: 0, width: BW, height: BH, opacity}}>
			<ScreenshotReveal
				src={src}
				width={BW}
				height={BH}
				startFrame={from}
				revealDurationInFrames={1}
				kenBurns={{fromScale: 1, toScale: 1.05}}
			/>
		</div>
	);
};

export const Scene05ClinicalPlanning: React.FC = () => {
	const frame = useCurrentFrame();
	const metricsOpacity = interpolate(frame, [70, 90, 320, 340], [0, 1, 1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{backgroundColor: COLORS.lightBg, alignItems: 'center'}}>
			<div style={{position: 'absolute', top: 90, left: 120}}>
				<SectionTitle
					headline="The computational work happens automatically."
					supporting="BMI, BMR, TDEE, and a full weekly meal structure — calculated instantly, reviewed by the doctor."
					startFrame={0}
					compact
				/>
			</div>
			<div style={{position: 'absolute', top: FRAME_TOP, left: '50%', transform: 'translateX(-50%)'}}>
				<BrowserFrame width={BW} height={BH} label="Patient Detail">
					{PHASES.map((p) => (
						<PhaseLayer key={p.src} {...p} />
					))}
					<FeatureCallout text="Add Custom Meal — doctor stays in control" startFrame={480} x={60} y={BH - 90} />

					<div
						style={{
							position: 'absolute',
							top: 24,
							right: 24,
							display: 'flex',
							gap: 40,
							backgroundColor: 'rgba(255,255,255,0.92)',
							borderRadius: 16,
							padding: '18px 28px',
							boxShadow: `0 20px 40px -16px ${COLORS.shadowColor}`,
							opacity: metricsOpacity,
						}}
					>
						<MetricCounter targetValue={21.8} label="BMI" startFrame={90} durationInFrames={24} dark={false} accentColor={COLORS.primaryTeal} decimals={1} size="small" />
						<MetricCounter targetValue={1281} label="BMR kcal/day" startFrame={110} durationInFrames={30} dark={false} accentColor={COLORS.primaryTeal} size="small" />
						<MetricCounter targetValue={1761} label="TDEE kcal/day" startFrame={130} durationInFrames={30} dark={false} accentColor={COLORS.accentGreen} size="small" />
					</div>
				</BrowserFrame>
			</div>
		</AbsoluteFill>
	);
};

import React from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';
import {SectionTitle} from '../components/SectionTitle';
import {BrowserFrame} from '../components/BrowserFrame';
import {ScreenshotReveal} from '../components/ScreenshotReveal';
import {FeatureCallout} from '../components/FeatureCallout';

const BW = 1300;
const BH = 731;
const FRAME_TOP = 260;

const FlowStep: React.FC<{label: string; x: number; startFrame: number; color: string}> = ({
	label,
	x,
	startFrame,
	color,
}) => {
	const frame = useCurrentFrame();
	const local = frame - startFrame;
	const opacity = interpolate(local, [0, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const y = interpolate(local, [0, 16], [16, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<div
			style={{
				position: 'absolute',
				left: x,
				top: 0,
				transform: `translateY(${y}px)`,
				opacity,
				backgroundColor: color,
				color: COLORS.white,
				fontFamily: FONT_FAMILY,
				fontWeight: 500,
				fontSize: 24,
				padding: '18px 30px',
				borderRadius: 16,
				whiteSpace: 'nowrap',
			}}
		>
			{label}
		</div>
	);
};

export const Scene06IndianNutrition: React.FC = () => {
	const frame = useCurrentFrame();
	const screenshotPhaseEnd = 520;
	const screenshotOpacity = interpolate(frame, [screenshotPhaseEnd - 20, screenshotPhaseEnd], [1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const flowOpacity = interpolate(frame, [screenshotPhaseEnd - 10, screenshotPhaseEnd + 20], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{backgroundColor: COLORS.lightBg, alignItems: 'center'}}>
			<div style={{position: 'absolute', top: 90, left: 120}}>
				<SectionTitle
					headline="Built on Indian food, not adapted to it."
					supporting="Over 2,100 recipes, tagged for diabetes, heart, kidney, and other clinical needs."
					startFrame={0}
					compact
				/>
			</div>

			<div
				style={{
					position: 'absolute',
					top: FRAME_TOP,
					left: '50%',
					transform: 'translateX(-50%)',
					opacity: screenshotOpacity,
				}}
			>
				<BrowserFrame width={BW} height={BH} label="Recipes">
					<ScreenshotReveal
						src={staticFile('screenshots/captured/doctor-recipes-fresh.png')}
						width={BW}
						height={BH}
						startFrame={40}
						revealDurationInFrames={24}
						kenBurns={{fromScale: 1, toScale: 1.07}}
					/>
					<FeatureCallout text="Clinical tags on every recipe" startFrame={140} x={60} y={180} />
					<FeatureCallout text="Meal-time & verification filters" startFrame={200} x={60} y={110} />
				</BrowserFrame>
			</div>

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
					opacity: flowOpacity,
				}}
			>
				<div style={{position: 'relative', width: 1400, height: 60}}>
					<FlowStep label="Patient condition" x={0} startFrame={screenshotPhaseEnd + 10} color={COLORS.primaryTeal} />
					<FlowStep label="Clinical rule engine" x={480} startFrame={screenshotPhaseEnd + 35} color={COLORS.secondaryOrange} />
					<FlowStep label="Compatible recipes" x={1000} startFrame={screenshotPhaseEnd + 60} color={COLORS.accentGreen} />
				</div>
			</div>
		</AbsoluteFill>
	);
};

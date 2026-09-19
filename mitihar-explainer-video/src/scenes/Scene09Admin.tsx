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

const Chip: React.FC<{label: string; startFrame: number; x: number}> = ({label, startFrame, x}) => {
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
				backgroundColor: COLORS.white,
				color: COLORS.textOnLight,
				fontFamily: FONT_FAMILY,
				fontWeight: 500,
				fontSize: 22,
				padding: '16px 28px',
				borderRadius: 14,
				boxShadow: `0 20px 40px -16px ${COLORS.shadowColor}`,
				border: `2px solid ${COLORS.primaryTeal}`,
				whiteSpace: 'nowrap',
			}}
		>
			{label}
		</div>
	);
};

export const Scene09Admin: React.FC = () => {
	const frame = useCurrentFrame();
	const screenshotEnd = 380;
	const screenshotOpacity = interpolate(frame, [screenshotEnd - 20, screenshotEnd], [1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const chipsOpacity = interpolate(frame, [screenshotEnd - 10, screenshotEnd + 20], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{backgroundColor: COLORS.lightBg, alignItems: 'center'}}>
			<div style={{position: 'absolute', top: 90, left: 120}}>
				<SectionTitle
					headline="Built for a clinic, not just a doctor."
					supporting="Role-based access, auditability, and controlled workflows across the team."
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
				<BrowserFrame width={BW} height={BH} label="Subscription Codes">
					<ScreenshotReveal
						src={staticFile('screenshots/existing/doctor-02-subscription-codes.png')}
						width={BW}
						height={BH}
						startFrame={40}
						revealDurationInFrames={24}
						kenBurns={{fromScale: 1, toScale: 1.06}}
					/>
					<FeatureCallout text="Clinic-issued activation codes" startFrame={140} x={60} y={140} />
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
					opacity: chipsOpacity,
				}}
			>
				<div style={{position: 'relative', width: 1300, height: 60}}>
					<Chip label="Role-based access" startFrame={screenshotEnd + 10} x={0} />
					<Chip label="Doctor-isolated patient data" startFrame={screenshotEnd + 35} x={420} />
					<Chip label="Audit-logged clinic actions" startFrame={screenshotEnd + 60} x={950} />
				</div>
			</div>
		</AbsoluteFill>
	);
};

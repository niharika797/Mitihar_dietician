import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';
import {LogoReveal} from '../components/LogoReveal';

const TEAM = ['Ruchit Das', 'Niharika Mishra', 'Achyut Maheshka'];

export const Scene12Outro: React.FC = () => {
	const frame = useCurrentFrame();

	const teamOpacity = interpolate(frame, [10, 30, 150, 175], [0, 1, 1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	const logoStart = 170;

	return (
		<AbsoluteFill
			style={{
				backgroundColor: COLORS.darkBg,
				alignItems: 'center',
				justifyContent: 'center',
			}}
		>
			<div
				style={{
					position: 'absolute',
					opacity: teamOpacity,
					display: 'flex',
					flexDirection: 'column',
					alignItems: 'center',
				}}
			>
				<div
					style={{
						fontFamily: FONT_FAMILY,
						fontWeight: 500,
						fontSize: 26,
						color: COLORS.textMuted,
						marginBottom: 24,
						letterSpacing: 2,
						textTransform: 'uppercase',
					}}
				>
					Built by
				</div>
				{TEAM.map((name) => (
					<div
						key={name}
						style={{
							fontFamily: FONT_FAMILY,
							fontWeight: 500,
							fontSize: 38,
							color: COLORS.textOnDark,
							marginBottom: 10,
						}}
					>
						{name}
					</div>
				))}
			</div>

			<div style={{opacity: interpolate(frame, [logoStart, logoStart + 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
				<LogoReveal
					variant="dark"
					startFrame={logoStart}
					width={180}
					taglineText={'Personalized nutrition. Clinical oversight.\nA more connected way to deliver dietary care.'}
				/>
			</div>

			<div
				style={{
					position: 'absolute',
					bottom: 70,
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: 18,
					color: COLORS.textMuted,
					opacity: interpolate(frame, [logoStart + 60, logoStart + 90], [0, 0.7], {
						extrapolateLeft: 'clamp',
						extrapolateRight: 'clamp',
					}),
				}}
			>
				[ Website / Contact — to be confirmed ]
			</div>
		</AbsoluteFill>
	);
};

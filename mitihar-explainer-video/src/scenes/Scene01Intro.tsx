import React from 'react';
import {AbsoluteFill} from 'remotion';
import {COLORS} from '../constants/brand';
import {LogoReveal} from '../components/LogoReveal';

export const Scene01Intro: React.FC = () => {
	return (
		<AbsoluteFill
			style={{
				backgroundColor: COLORS.darkBg,
				alignItems: 'center',
				justifyContent: 'center',
			}}
		>
			<LogoReveal
				variant="dark"
				startFrame={10}
				width={220}
				taglineText={
					'Clinical nutrition is deeply personal.\nBut the way it is planned, delivered, and tracked is still largely manual.'
				}
			/>
		</AbsoluteFill>
	);
};

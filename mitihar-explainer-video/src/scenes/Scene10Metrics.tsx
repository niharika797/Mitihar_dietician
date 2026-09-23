import React from 'react';
import {AbsoluteFill} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';
import {MetricCounter} from '../components/MetricCounter';

export const Scene10Metrics: React.FC = () => {
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
					fontFamily: FONT_FAMILY,
					fontWeight: 500,
					fontSize: 40,
					color: COLORS.textOnDark,
					marginBottom: 70,
				}}
			>
				Verified, not promised.
			</div>
			<div style={{display: 'flex', gap: 90}}>
				<MetricCounter
					targetValue={2120}
					suffix="+"
					label="Indian recipes in the database"
					startFrame={10}
					durationInFrames={40}
					accentColor={COLORS.accentGreen}
				/>
				<MetricCounter
					targetValue={150}
					suffix="+"
					label="Clinical API endpoints"
					startFrame={20}
					durationInFrames={40}
					accentColor={COLORS.accentGreen}
				/>
				<MetricCounter
					targetValue={1000}
					label="Concurrent users load-tested"
					startFrame={30}
					durationInFrames={40}
					accentColor={COLORS.secondaryOrange}
				/>
				<MetricCounter
					targetValue={103}
					label="Automated integration checks"
					startFrame={40}
					durationInFrames={40}
					accentColor={COLORS.accentGreen}
				/>
				<MetricCounter
					targetValue={178}
					label="Engineering commits"
					startFrame={50}
					durationInFrames={40}
					accentColor={COLORS.accentGreen}
				/>
			</div>
		</AbsoluteFill>
	);
};

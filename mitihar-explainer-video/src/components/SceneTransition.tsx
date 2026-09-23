import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {TRANSITION_OVERLAP} from '../constants/timing';

interface Props {
	durationInFrames: number;
	fadeIn?: boolean;
	fadeOut?: boolean;
	children: React.ReactNode;
}

export const SceneTransition: React.FC<Props> = ({
	durationInFrames,
	fadeIn = true,
	fadeOut = true,
	children,
}) => {
	const frame = useCurrentFrame();

	const inOpacity = fadeIn
		? interpolate(frame, [0, TRANSITION_OVERLAP], [0, 1], {
				extrapolateLeft: 'clamp',
				extrapolateRight: 'clamp',
			})
		: 1;

	const outOpacity = fadeOut
		? interpolate(
				frame,
				[durationInFrames - TRANSITION_OVERLAP, durationInFrames],
				[1, 0],
				{extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
			)
		: 1;

	return <AbsoluteFill
		style={{
			opacity: Math.min(inOpacity, outOpacity)
		}}
	>{children}</AbsoluteFill>;
};

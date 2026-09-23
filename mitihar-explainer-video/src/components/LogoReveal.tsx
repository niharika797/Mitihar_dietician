import React from 'react';
import {Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT_FAMILY} from '../constants/brand';

interface Props {
	variant: 'light' | 'dark';
	taglineText?: string;
	startFrame: number;
	width?: number;
}

export const LogoReveal: React.FC<Props> = ({
	variant,
	taglineText,
	startFrame,
	width = 480,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const local = frame - startFrame;

	const src = variant === 'light' ? staticFile('brand/logo-light-bg.svg') : staticFile('brand/logo-dark-bg.svg');
	// logo-light-bg.svg is the full wordmark (900x640); logo-dark-bg.svg is a square mark only (196x196).
	const aspect = variant === 'light' ? 900 / 640 : 1;

	const scaleSpring = spring({
		frame: local,
		fps,
		config: {damping: 12, mass: 0.9, stiffness: 100},
	});
	const scale = interpolate(scaleSpring, [0, 1], [0.85, 1]);
	const opacity = interpolate(local, [0, 20], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	const taglineSpring = spring({
		frame: local - 18,
		fps,
		config: {damping: 200, stiffness: 120, mass: 0.9},
	});
	const taglineY = interpolate(taglineSpring, [0, 1], [16, 0]);
	const taglineOpacity = interpolate(local, [18, 34], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	return (
		<div
			style={{
				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
				justifyContent: 'center',
			}}
		>
			<Img
				src={src}
				style={{
					width,
					height: width / aspect,
					opacity,
					transform: `scale(${scale})`,
					objectFit: 'contain',
					translate: '-8px 1.7px'
				}}
			/>
			{taglineText ? (
				<p
					style={{
						fontFamily: FONT_FAMILY,
						fontWeight: 500,
						fontSize: 30,
						color: variant === 'dark' ? COLORS.textOnDark : COLORS.textOnLight,
						marginTop: 32,
						opacity: taglineOpacity,
						transform: `translateY(${taglineY}px)`,
						textAlign: 'center',
						maxWidth: 900,
						whiteSpace: 'pre-line',
					}}
				>
					{taglineText}
				</p>
			) : null}
		</div>
	);
};

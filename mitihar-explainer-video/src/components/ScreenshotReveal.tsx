import React from 'react';
import {Img, interpolate, useCurrentFrame} from 'remotion';
import {COLORS} from '../constants/brand';

interface KenBurns {
	fromScale: number;
	toScale: number;
	fromX?: number;
	toX?: number;
	fromY?: number;
	toY?: number;
}

interface HighlightRect {
	x: number; // 0-1 fraction of frame width
	y: number; // 0-1 fraction of frame height
	w: number; // 0-1 fraction
	h: number; // 0-1 fraction
	startFrame: number;
	durationInFrames?: number;
}

interface Props {
	src: string;
	width: number;
	height: number;
	startFrame: number;
	revealDurationInFrames?: number;
	kenBurns?: KenBurns;
	highlightRect?: HighlightRect;
	/** Crop out unwanted top/bottom pixel strips from the source image (e.g. a dev-only toast). */
	cropTopPx?: number;
	cropBottomPx?: number;
	naturalHeightPx?: number;
}

export const ScreenshotReveal: React.FC<Props> = ({
	src,
	width,
	height,
	startFrame,
	revealDurationInFrames = 24,
	kenBurns,
	highlightRect,
	cropTopPx = 0,
	cropBottomPx = 0,
	naturalHeightPx,
}) => {
	const frame = useCurrentFrame();
	const local = frame - startFrame;

	const revealPct = interpolate(local, [0, revealDurationInFrames], [0, 100], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	let imgTransform = 'none';
	if (kenBurns) {
		const scale = interpolate(local, [0, height], [kenBurns.fromScale, kenBurns.toScale], {
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		});
		const tx = interpolate(local, [0, height], [kenBurns.fromX ?? 0, kenBurns.toX ?? 0], {
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		});
		const ty = interpolate(local, [0, height], [kenBurns.fromY ?? 0, kenBurns.toY ?? 0], {
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		});
		imgTransform = `scale(${scale}) translate(${tx}px, ${ty}px)`;
	}

	const cropScale = naturalHeightPx
		? naturalHeightPx / (naturalHeightPx - cropTopPx - cropBottomPx)
		: 1;
	const cropShiftPx = naturalHeightPx ? (cropTopPx - cropBottomPx) / 2 : 0;

	return (
		<div
			style={{
				width,
				height,
				overflow: 'hidden',
				position: 'relative',
				clipPath: `inset(0 ${100 - revealPct}% 0 0)`,
			}}
		>
			<div
				style={{
					width,
					height,
					overflow: 'hidden',
					position: 'relative',
					transform: imgTransform,
					transformOrigin: 'center center',
				}}
			>
				<Img
					src={src}
					style={{
						width,
						height,
						objectFit: 'cover',
						objectPosition: 'top',
						transform: `scale(${cropScale}) translateY(${-cropShiftPx}px)`,
						transformOrigin: 'top center',
						scale: 0.919,
						translate: '0px 35.1px'
					}}
				/>
			</div>
			{highlightRect ? (
				<HighlightOverlay width={width} height={height} rect={highlightRect} />
			) : null}
		</div>
	);
};

const HighlightOverlay: React.FC<{width: number; height: number; rect: HighlightRect}> = ({
	width,
	height,
	rect,
}) => {
	const frame = useCurrentFrame();
	const local = frame - rect.startFrame;
	const duration = rect.durationInFrames ?? 20;
	const opacity = interpolate(local, [0, duration], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	if (opacity <= 0) return null;

	const rx = rect.x * width;
	const ry = rect.y * height;
	const rw = rect.w * width;
	const rh = rect.h * height;

	return (
		<svg
			width={width}
			height={height}
			style={{position: 'absolute', top: 0, left: 0, opacity, pointerEvents: 'none'}}
		>
			<defs>
				<mask id="spotlight-mask">
					<rect x={0} y={0} width={width} height={height} fill="white" />
					<rect x={rx} y={ry} width={rw} height={rh} rx={12} fill="black" />
				</mask>
			</defs>
			<rect
				x={0}
				y={0}
				width={width}
				height={height}
				fill="rgba(11,15,14,0.45)"
				mask="url(#spotlight-mask)"
			/>
			<rect
				x={rx}
				y={ry}
				width={rw}
				height={rh}
				rx={12}
				fill="none"
				stroke={COLORS.accentGreen}
				strokeWidth={4}
			/>
		</svg>
	);
};

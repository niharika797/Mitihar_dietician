import React from 'react';

interface Props {
	width: number;
	height: number;
	children: React.ReactNode;
}

// A single restrained iPhone-style bezel. One device style is enough for this brief.
export const DeviceFrame: React.FC<Props> = ({width, height, children}) => {
	const bezel = Math.round(width * 0.035);
	const cornerRadius = Math.round(width * 0.13);
	const screenRadius = cornerRadius - bezel * 0.6;

	return (
		<div
			style={{
				width: width + bezel * 2,
				height: height + bezel * 2,
				borderRadius: cornerRadius,
				backgroundColor: '#111318',
				boxShadow: '0 50px 100px -25px rgba(11,15,14,0.35), inset 0 0 0 2px rgba(255,255,255,0.06)',
				position: 'relative',
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
			}}
		>
			<div
				style={{
					width,
					height,
					borderRadius: screenRadius,
					overflow: 'hidden',
					position: 'relative',
					backgroundColor: '#FFFFFF',
				}}
			>
				{children}
			</div>
			{/* dynamic island */}
			<div
				style={{
					position: 'absolute',
					top: bezel + 14,
					left: '50%',
					transform: 'translateX(-50%)',
					width: width * 0.28,
					height: Math.round(width * 0.045),
					borderRadius: 999,
					backgroundColor: '#111318',
				}}
			/>
		</div>
	);
};

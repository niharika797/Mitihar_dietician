import React from 'react';
import {COLORS} from '../constants/brand';

interface Props {
	width: number;
	height: number;
	label?: string;
	children: React.ReactNode;
}

const DOT_COLORS = ['#FF5F57', '#FEBC2E', '#28C840'];

export const BrowserFrame: React.FC<Props> = ({width, height, label, children}) => {
	const chromeHeight = 44;

	return (
		<div
			style={{
				width,
				height: height + chromeHeight,
				borderRadius: 16,
				overflow: 'hidden',
				boxShadow: `0 40px 80px -20px ${COLORS.shadowColor}`,
				backgroundColor: '#E5E7EB',
			}}
		>
			<div
				style={{
					height: chromeHeight,
					display: 'flex',
					alignItems: 'center',
					paddingLeft: 20,
					paddingRight: 20,
					backgroundColor: '#F1F2F4',
					position: 'relative',
				}}
			>
				<div style={{display: 'flex', gap: 8}}>
					{DOT_COLORS.map((c) => (
						<div
							key={c}
							style={{
								width: 12,
								height: 12,
								borderRadius: 6,
								backgroundColor: c,
							}}
						/>
					))}
				</div>
				{label ? (
					<div
						style={{
							position: 'absolute',
							left: '50%',
							transform: 'translateX(-50%)',
							backgroundColor: '#FFFFFF',
							borderRadius: 8,
							padding: '5px 18px',
							fontSize: 14,
							color: '#6B7280',
							fontFamily: 'inherit',
						}}
					>
						{label}
					</div>
				) : null}
			</div>
			<div style={{width, height, overflow: 'hidden', position: 'relative'}}>{children}</div>
		</div>
	);
};

import React from 'react';
import {Composition, Series} from 'remotion';
import {FPS, HEIGHT, SCENES, TOTAL_DURATION_IN_FRAMES, TRANSITION_OVERLAP, WIDTH} from './constants/timing';
import {SceneTransition} from './components/SceneTransition';

import {Scene01Intro} from './scenes/Scene01Intro';
import {Scene02Problem} from './scenes/Scene02Problem';
import {Scene03Platform} from './scenes/Scene03Platform';
import {Scene04DoctorDashboard} from './scenes/Scene04DoctorDashboard';
import {Scene05ClinicalPlanning} from './scenes/Scene05ClinicalPlanning';
import {Scene06IndianNutrition} from './scenes/Scene06IndianNutrition';
import {Scene07PatientApp} from './scenes/Scene07PatientApp';
import {Scene08Pantry} from './scenes/Scene08Pantry';
import {Scene09Admin} from './scenes/Scene09Admin';
import {Scene10Metrics} from './scenes/Scene10Metrics';
import {Scene11Objectives} from './scenes/Scene11Objectives';
import {Scene12Outro} from './scenes/Scene12Outro';

const SCENE_COMPONENTS: Record<string, React.FC> = {
	Scene01Intro,
	Scene02Problem,
	Scene03Platform,
	Scene04DoctorDashboard,
	Scene05ClinicalPlanning,
	Scene06IndianNutrition,
	Scene07PatientApp,
	Scene08Pantry,
	Scene09Admin,
	Scene10Metrics,
	Scene11Objectives,
	Scene12Outro,
};

const MitiharExplainer: React.FC = () => {
	return (
		<Series>
			{SCENES.map((scene, index) => {
				const SceneComponent = SCENE_COMPONENTS[scene.id];
				return (
					<Series.Sequence
						key={scene.id}
						durationInFrames={scene.durationInFrames}
						offset={index === 0 ? 0 : -TRANSITION_OVERLAP}
						layout="none"
					>
						<SceneTransition
							durationInFrames={scene.durationInFrames}
							fadeIn={index !== 0}
							fadeOut={index !== SCENES.length - 1}
						>
							<SceneComponent />
						</SceneTransition>
					</Series.Sequence>
				);
			})}
		</Series>
	);
};

export const RemotionRoot: React.FC = () => {
	return (
		<Composition
			id="MitiharExplainer"
			component={MitiharExplainer}
			durationInFrames={TOTAL_DURATION_IN_FRAMES}
			fps={FPS}
			width={WIDTH}
			height={HEIGHT}
		/>
	);
};

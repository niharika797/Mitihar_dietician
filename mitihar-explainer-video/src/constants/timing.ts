export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const TRANSITION_OVERLAP = 15; // 0.5s crossfade between adjacent scenes

export interface SceneTiming {
	id: string;
	durationInFrames: number;
}

// Frame budgets are each scene's OWN duration (before overlap is subtracted).
// Total on the master timeline = sum(durations) - overlap * (scenes.length - 1).
export const SCENES: SceneTiming[] = [
	{id: 'Scene01Intro', durationInFrames: 450}, // 15.0s
	{id: 'Scene02Problem', durationInFrames: 750}, // 25.0s
	{id: 'Scene03Platform', durationInFrames: 600}, // 20.0s
	{id: 'Scene04DoctorDashboard', durationInFrames: 990}, // 33.0s
	{id: 'Scene05ClinicalPlanning', durationInFrames: 900}, // 30.0s
	{id: 'Scene06IndianNutrition', durationInFrames: 810}, // 27.0s
	{id: 'Scene07PatientApp', durationInFrames: 1050}, // 35.0s
	{id: 'Scene08Pantry', durationInFrames: 600}, // 20.0s
	{id: 'Scene09Admin', durationInFrames: 600}, // 20.0s
	{id: 'Scene10Metrics', durationInFrames: 450}, // 15.0s
	{id: 'Scene11Objectives', durationInFrames: 540}, // 18.0s
	{id: 'Scene12Outro', durationInFrames: 375}, // 12.5s
];

export const TOTAL_DURATION_IN_FRAMES =
	SCENES.reduce((sum, s) => sum + s.durationInFrames, 0) -
	TRANSITION_OVERLAP * (SCENES.length - 1);

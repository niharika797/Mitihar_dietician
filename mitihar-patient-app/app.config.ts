import { ExpoConfig, ConfigContext } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "Mitihar",
  slug: "mitihar-patient-app",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/images/icon.png",
  scheme: "mitihar",
  userInterfaceStyle: "light",
  splash: {
    image: "./assets/images/splash-icon.png",
    resizeMode: "contain",
    backgroundColor: "#1E7C45",
  },
  ios: {
    supportsTablet: false,
    bundleIdentifier: "com.mitihar.patient",
  },
  android: {
    adaptiveIcon: {
      foregroundImage: "./assets/images/adaptive-icon.png",
      backgroundColor: "#1E7C45",
    },
    package: "com.mitihar.patient",
  },
  web: {
    bundler: "metro",
    output: "static",
    favicon: "./assets/images/favicon.png",
  },
  plugins: [
    "expo-router",
    "expo-secure-store",
    "expo-image",
    [
      "expo-build-properties",
      {
        android: { compileSdkVersion: 35, targetSdkVersion: 35, buildToolsVersion: "35.0.0" },
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
  },
  extra: {
    apiUrl: process.env.EXPO_PUBLIC_API_URL,
    googleClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID,
    eas: { projectId: process.env.EXPO_PUBLIC_EAS_PROJECT_ID ?? "your-eas-project-id" },
  },
});

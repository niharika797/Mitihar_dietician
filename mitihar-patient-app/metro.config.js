const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");
const path = require("path");

const config = getDefaultConfig(__dirname);

// Zustand v5 ships ESM (esm/middleware.mjs) that uses import.meta.env which
// Metro bundles into a non-module <script> tag and throws at runtime on web.
// Force resolution to the CJS build for all zustand sub-paths.
const _resolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (platform === "web" && moduleName.startsWith("zustand")) {
    const zustandRoot = path.dirname(
      require.resolve("zustand/package.json", { paths: [context.originModulePath] })
    );
    const subPath = moduleName === "zustand" ? "index.js" : moduleName.replace(/^zustand\//, "") + ".js";
    return { filePath: path.join(zustandRoot, subPath), type: "sourceFile" };
  }
  if (_resolveRequest) return _resolveRequest(context, moduleName, platform);
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = withNativeWind(config, { input: "./global.css" });

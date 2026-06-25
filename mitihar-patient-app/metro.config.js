const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");
const path = require("path");

const config = getDefaultConfig(__dirname);

// Zustand v5 ships ESM (esm/middleware.mjs) that uses import.meta.env which
// Metro bundles into a non-module <script> tag and throws at runtime on web.
// Force resolution to the CJS build for all zustand sub-paths.
const fs = require("fs");
const _resolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (platform === "web" && moduleName.startsWith("zustand")) {
    const zustandRoot = path.dirname(
      require.resolve("zustand/package.json", { paths: [context.originModulePath] })
    );
    const subPath = moduleName === "zustand" ? "index.js" : moduleName.replace(/^zustand\//, "") + ".js";
    return { filePath: path.join(zustandRoot, subPath), type: "sourceFile" };
  }

  // react-native-web/dist/index.js (ESM) exports use relative directory imports
  // (e.g. './exports/DeviceEventEmitter') that Metro fails to resolve as directory
  // indexes on Windows. Redirect them to their CJS counterparts in dist/cjs/.
  if (
    platform === "web" &&
    moduleName.startsWith("./") &&
    context.originModulePath.replace(/\\/g, "/").endsWith("react-native-web/dist/index.js")
  ) {
    const rnwRoot = path.dirname(
      require.resolve("react-native-web/package.json", { paths: [context.originModulePath] })
    );
    const subName = moduleName.slice(2); // strip leading "./"
    // Try directory index first (most exports use this pattern)
    const dirIndex = path.join(rnwRoot, "dist/cjs", subName, "index.js");
    if (fs.existsSync(dirIndex)) return { filePath: dirIndex, type: "sourceFile" };
    // Fallback: direct .js file
    const directFile = path.join(rnwRoot, "dist/cjs", subName + ".js");
    if (fs.existsSync(directFile)) return { filePath: directFile, type: "sourceFile" };
  }

  if (_resolveRequest) return _resolveRequest(context, moduleName, platform);
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = withNativeWind(config, { input: "./global.css" });

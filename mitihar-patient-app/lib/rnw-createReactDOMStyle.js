// react-native-reanimated (web) does `require("react-native-web/dist/exports/StyleSheet/compiler/createReactDOMStyle").default`.
// The CJS build of that file ends with `module.exports = exports.default`, so `.default` is undefined there and every
// animated style crashed with "Cannot convert undefined or null to object" on each frame. metro.config.js points that one
// import here so react-native-web can be loaded from a single (CJS) build.
const createReactDOMStyle = require("react-native-web/dist/cjs/exports/StyleSheet/compiler/createReactDOMStyle");

module.exports = { __esModule: true, default: createReactDOMStyle };

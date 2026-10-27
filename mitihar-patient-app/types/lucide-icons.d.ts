// lib/icons.ts imports each icon from its own file (see the note there); those files ship without types.
declare module "lucide-react-native/dist/esm/icons/*" {
  import type { LucideIcon } from "lucide-react-native";
  const icon: LucideIcon;
  export default icon;
}

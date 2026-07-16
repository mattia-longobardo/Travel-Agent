import { maskableIcon } from "@/lib/brandMark";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

// iOS home-screen icon: full teal square + white plane (iOS applies its own rounding).
export default function AppleIcon() {
  return maskableIcon(size.width);
}

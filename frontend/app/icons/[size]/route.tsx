import { maskableIcon } from "@/lib/brandMark";

// Maskable PNG icons referenced by the web app manifest. Prerendered at build time
// for the two sizes Chrome wants for installability.
export const dynamicParams = false;

export function generateStaticParams() {
  return [{ size: "192" }, { size: "512" }];
}

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ size: string }> },
) {
  const { size } = await ctx.params;
  return maskableIcon(Number(size));
}

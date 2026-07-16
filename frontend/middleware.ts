import { NextResponse, type NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const authed = req.cookies.has("travel_session");
  const p = req.nextUrl.pathname;
  if (!authed && (p === "/" || p.startsWith("/settings") || p.startsWith("/admin") || p.startsWith("/stays"))) {
    return NextResponse.redirect(new URL("/login", req.url));
  }
  return NextResponse.next();
}

export const config = { matcher: ["/", "/settings/:path*", "/admin/:path*", "/stays/:path*"] };

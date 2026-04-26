import { NextResponse } from "next/server";

import { auth } from "@/auth";

export default auth((req) => {
  // Brak whitelisty (dev) — przepuść.
  const allowed = (process.env.AUTH_ALLOWED_EMAILS || "").trim();
  if (!allowed) return NextResponse.next();

  if (!req.auth) {
    const url = new URL("/login", req.url);
    url.searchParams.set("callbackUrl", req.nextUrl.pathname + req.nextUrl.search);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
});

export const config = {
  // Chroni wszystko poza:
  // - /api/auth (NextAuth callbacks)
  // - /_next (statics + RSC)
  // - /favicon.ico, /login (publiczne)
  matcher: ["/((?!api/auth|_next|favicon.ico|login).*)"],
};

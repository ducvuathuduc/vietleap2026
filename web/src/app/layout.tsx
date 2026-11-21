import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import "./globals.css";

import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { localizedMetadata, requestLanguage } from "@/lib/npl/locale";
import { SITE_TITLE } from "@/lib/npl/view";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin", "vietnamese"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const lang = await requestLanguage();
  const description = lang === "vi"
    ? "Khung đánh giá chất lượng tín dụng và cảnh báo rủi ro."
    : "A framework for assessing credit quality and early warning signs.";
  return { ...localizedMetadata(lang, SITE_TITLE[lang], description), robots: { index: true, follow: true } };
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const lang = await requestLanguage();
  return (
    <html
      lang={lang}
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="font-sans min-h-full flex flex-col">
        <ThemeProvider attribute="class" forcedTheme="light" enableSystem={false} disableTransitionOnChange>
          <NuqsAdapter>{children}</NuqsAdapter>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}

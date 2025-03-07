import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Script from 'next/script';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Smart Notes App",
  description: "A notes application built with PyFlow.ts",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      {/* Add a script that runs before React hydration to suppress warnings */}
      <Script id="suppress-hydration-warning" strategy="beforeInteractive">
        {`
          // Suppress hydration warnings from browser extensions
          window.__NEXT_HYDRATION_WARNINGS_SUPPRESSED__ = true;
          window.__NEXT_HYDRATION_SUPPRESSED_ATTR__ = ["data-lt-installed"];

          // Original error handler
          const originalError = console.error;

          // Replace console.error to filter hydration warnings
          console.error = function() {
            if (
              arguments[0] &&
              typeof arguments[0] === 'string' &&
              arguments[0].includes('Hydration failed')
            ) {
              // Filter out hydration errors related to browser extensions
              if (
                arguments[1] &&
                arguments[1].includes &&
                (arguments[1].includes('data-lt-installed') ||
                 arguments[1].includes('data-grammarly'))
              ) {
                return;
              }
            }

            // Call original handler for other errors
            return originalError.apply(this, arguments);
          };
        `}
      </Script>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { Manrope, Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "react-hot-toast";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FraudShield AI – Fraud Detection System",
  description: "AI-powered fraud detection and prevention platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${manrope.variable} ${inter.variable}`}>
      <body className="bg-background text-on-surface font-body antialiased">
        <Providers>
          <Toaster
            position="top-right"
            toastOptions={{
              className: "bg-surface-container-high text-on-surface border border-outline-variant",
              duration: 4000,
            }}
          />
          {children}
        </Providers>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CareCall AI",
  description:
    "AI voice receptionist for dental and healthcare clinics in Alberta.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}

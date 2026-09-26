import type { Metadata } from "next";
import "./globals.css";
import Shell from "@/app/components/Shell";

export const metadata: Metadata = {
  title: "EdgeAtlas Terminal",
  description: "Prediction-market intelligence and execution terminal",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}

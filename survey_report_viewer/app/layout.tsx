import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Survey Report Viewer",
  description: "View and query survey analysis reports",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}


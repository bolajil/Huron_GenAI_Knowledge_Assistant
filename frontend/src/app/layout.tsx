import type { Metadata } from "next";
import { Inter, Fira_Code } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "../components/theme-provider";
import { Toaster } from "../components/ui/toaster";
import { AuthProvider } from "../contexts/auth-context";
import { PostHogProvider } from "../components/providers/PostHogProvider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const firaCode = Fira_Code({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Huron GenAI Knowledge Assistant",
  description: "Enterprise AI-powered knowledge management system",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${firaCode.variable} font-sans antialiased bg-sky-100`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <AuthProvider>
            <PostHogProvider>
              {children}
              <Toaster />
            </PostHogProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

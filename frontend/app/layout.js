import "./globals.css";

export const metadata = {
  title: "AI Assignment Evaluator"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

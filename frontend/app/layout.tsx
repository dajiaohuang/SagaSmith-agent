import "./styles.css";

export const metadata = {
  title: "DND DM Agent",
  description: "Local-first DND Dungeon Master console",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}


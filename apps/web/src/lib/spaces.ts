export const SPACES = [
  { id: "today", label: "Today", href: "/today", icon: "⌂" },
  { id: "agents", label: "Agents & Automation", href: "/agents", icon: "◈" },
  { id: "create", label: "Create", href: "/create", icon: "✎" },
  { id: "knowledge", label: "Knowledge", href: "/knowledge", icon: "◉" },
  { id: "wealth", label: "Wealth", href: "/wealth", icon: "$" },
  { id: "life", label: "Life", href: "/life", icon: "♡" },
  { id: "infrastructure", label: "Infrastructure", href: "/infrastructure", icon: "▣" },
  { id: "insights", label: "Insights", href: "/insights", icon: "◎" },
  { id: "system", label: "System", href: "/system", icon: "⚙" },
] as const;

export type SpaceId = (typeof SPACES)[number]["id"];

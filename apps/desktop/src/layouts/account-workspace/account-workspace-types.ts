export type AccountSwitcherOption = {
  id: string;
  name: string;
  username: string | null;
  status: "draft" | "unbound" | "ready" | "attention" | "archived";
  positioningSummary: string | null;
};

export type AccountWorkspaceNavItem = {
  id: string;
  path: string;
  title: string;
  icon: string;
};

export type ShellFeedback = {
  id: string;
  tone: "info" | "warning" | "danger";
  message: string;
  logId?: string | null;
  retryable?: boolean;
};

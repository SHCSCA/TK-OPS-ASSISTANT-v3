import { IconAlertCircle, IconCheck, IconInfoCircle } from "@tabler/icons-react";

const icons = {
  danger: IconAlertCircle,
  info: IconInfoCircle,
  success: IconCheck,
};

export function ToastRegion({ toast }) {
  if (!toast) return null;
  const Icon = icons[toast.tone] || IconInfoCircle;
  return (
    <div className={`toast toast--${toast.tone}`} role="status">
      <Icon size={18} stroke={2} />
      <span>{toast.message}</span>
    </div>
  );
}

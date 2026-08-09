export function AccountAvatar({ account, size = "md" }) {
  return (
    <span className={`account-avatar account-avatar--${size}`} data-account={account.id} aria-hidden="true">
      {account.initials}
      <i className={`account-avatar__status account-avatar__status--${account.status}`} />
    </span>
  );
}

export const productionArtifactKinds = [
  "desktop",
  "sidecar",
  "installer",
  "portable"
];

export const productionTestIds = [
  "runtime-full",
  "desktop-active",
  "desktop-typecheck",
  "rust-tauri",
  "playwright-first-run",
  "playwright-account-workspace",
  "sidecar-smoke",
  "windows-gui-smoke",
  "windows-installer-smoke",
  "packaged-license-activation",
  "p0-h-real-provider-execution",
  "target-tiktok-supervised-login"
];

export const artifactBoundEvidence = {
  "windows-gui-smoke": ["desktop", "portable"],
  "windows-installer-smoke": ["installer"],
  "packaged-license-activation": ["desktop", "sidecar"],
  "p0-h-real-provider-execution": [
    "desktop",
    "sidecar",
    "installer",
    "portable"
  ],
  "target-tiktok-supervised-login": ["desktop", "sidecar", "installer"]
};

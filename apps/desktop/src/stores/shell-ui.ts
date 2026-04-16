import { defineStore } from "pinia";

export const useShellUiStore = defineStore("shell-ui", {
  state: () => ({
    isDetailPanelOpen: false
  }),
  actions: {
    openDetailPanel() {
      this.isDetailPanelOpen = true;
    },
    closeDetailPanel() {
      this.isDetailPanelOpen = false;
    },
    toggleDetailPanel() {
      this.isDetailPanelOpen = !this.isDetailPanelOpen;
    }
  }
});

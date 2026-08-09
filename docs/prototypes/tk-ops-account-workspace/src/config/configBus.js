import { prototypeConfig } from "./prototypeConfig.js";
import { prototypeLogger } from "../utils/logger.js";

export const configBus = {
  loadTheme() {
    try {
      return localStorage.getItem(prototypeConfig.storageKeys.theme) || "light";
    } catch (error) {
      prototypeLogger.error("读取主题配置失败", error);
      return "light";
    }
  },

  saveTheme(theme) {
    try {
      localStorage.setItem(prototypeConfig.storageKeys.theme, theme);
    } catch (error) {
      prototypeLogger.error("保存主题配置失败", error);
    }
  },
};

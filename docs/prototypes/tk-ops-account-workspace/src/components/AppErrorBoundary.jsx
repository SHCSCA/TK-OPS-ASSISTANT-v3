import React from "react";
import { IconAlertCircle, IconRefresh } from "@tabler/icons-react";
import { prototypeLogger } from "../utils/logger.js";

export class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    prototypeLogger.error("原型界面渲染失败", { error: error.message, stack: info.componentStack });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="fatal-state">
        <IconAlertCircle size={30} />
        <h1>界面加载失败</h1>
        <p>错误已经记录，请刷新原型后重试。</p>
        <button className="primary-button" onClick={() => window.location.reload()} type="button"><IconRefresh size={17} />刷新原型</button>
      </main>
    );
  }
}

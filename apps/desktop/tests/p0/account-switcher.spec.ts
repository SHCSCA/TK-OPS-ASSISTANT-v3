import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import AccountSwitcher from "@/layouts/account-workspace/AccountSwitcher.vue";
import type { AccountSwitcherOption } from "@/layouts/account-workspace/account-workspace-types";

describe("P0 账号切换器", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("通过 Teleport 展示完整账号菜单并支持搜索", async () => {
    const wrapper = mount(AccountSwitcher, {
      attachTo: document.body,
      props: defaultProps()
    });
    await nextTick();

    const menu = document.querySelector<HTMLElement>("#account-switcher-menu");
    expect(menu).not.toBeNull();
    expect(menu?.parentElement).toBe(document.body);
    expect(menu?.style.width).toBe("320px");
    expect(menu?.style.left).toBe("12px");
    expect(document.body.textContent).toContain("这是一个很长但仍需完整处理的账号名称");

    const search = menu?.querySelector<HTMLInputElement>('input[type="search"]');
    expect(search).not.toBeNull();
    if (search) {
      search.value = "不存在";
      search.dispatchEvent(new Event("input"));
    }
    await nextTick();
    expect(menu?.textContent).toContain("没有匹配账号");
    wrapper.unmount();
  });

  it("按 Escape 或点击菜单外部时请求关闭且恢复触发器焦点", async () => {
    const wrapper = mount(AccountSwitcher, {
      attachTo: document.body,
      props: defaultProps()
    });
    await nextTick();

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(wrapper.emitted("close")).toHaveLength(1);

    document.body.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    expect(wrapper.emitted("close")).toHaveLength(2);

    await wrapper.setProps({ open: false });
    await nextTick();
    expect(document.activeElement).toBe(
      wrapper.get<HTMLButtonElement>(".account-switcher__trigger").element
    );
    wrapper.unmount();
  });

  it("后台刷新开始时主动关闭账号菜单，避免禁用选项停留在界面", async () => {
    const wrapper = mount(AccountSwitcher, {
      attachTo: document.body,
      props: defaultProps()
    });
    await nextTick();

    await wrapper.setProps({ disabled: true });
    await nextTick();

    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
  });
});

function defaultProps() {
  const accounts: AccountSwitcherOption[] = [
    {
      id: "account-alpha",
      name: "这是一个很长但仍需完整处理的账号名称",
      username: "alpha_creator",
      status: "ready",
      positioningSummary: "效率工具测评"
    },
    {
      id: "account-archived",
      name: "归档账号",
      username: null,
      status: "archived",
      positioningSummary: null
    }
  ];
  return {
    accounts,
    currentAccount: accounts[0],
    currentAccountId: accounts[0].id,
    disabled: false,
    open: true
  };
}

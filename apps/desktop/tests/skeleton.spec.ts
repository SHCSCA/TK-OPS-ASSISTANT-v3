/**
 * Skeleton 组件测试
 */
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import Skeleton from "@/components/ui/Skeleton/Skeleton.vue";

describe("Skeleton.vue", () => {
  it("应渲染为 div 元素", () => {
    const wrapper = mount(Skeleton);
    expect(wrapper.element.tagName).toBe("DIV");
  });

  it("默认应有 ui-skeleton 和变体 class", () => {
    const wrapper = mount(Skeleton);
    expect(wrapper.classes()).toContain("ui-skeleton");
    expect(wrapper.classes()).toContain("ui-skeleton--text");
    expect(wrapper.classes()).toContain("ui-skeleton--full");
    expect(wrapper.classes()).toContain("ui-skeleton--sm");
  });

  it("应支持 circle 变体", () => {
    const wrapper = mount(Skeleton, { props: { variant: "circle" } });
    expect(wrapper.classes()).toContain("ui-skeleton--circle");
  });

  it("应支持 rect 变体", () => {
    const wrapper = mount(Skeleton, { props: { variant: "rect" } });
    expect(wrapper.classes()).toContain("ui-skeleton--rect");
  });

  it("应支持 card 变体", () => {
    const wrapper = mount(Skeleton, { props: { variant: "card" } });
    expect(wrapper.classes()).toContain("ui-skeleton--card");
  });

  it("应支持自定义宽度", () => {
    const wrapper = mount(Skeleton, { props: { width: "1/2" } });
    expect(wrapper.attributes("class")).toContain("ui-skeleton--1/2");
  });

  it("应设置 aria-busy=true", () => {
    const wrapper = mount(Skeleton);
    expect(wrapper.attributes("aria-busy")).toBe("true");
  });

  it("应包含 sr-only 加载提示", () => {
    const wrapper = mount(Skeleton);
    const srOnly = wrapper.find(".sr-only");
    expect(srOnly.exists()).toBe(true);
    expect(srOnly.text()).toBe("加载中");
  });

  it("customWidth/customHeight 应生成内联样式", () => {
    const wrapper = mount(Skeleton, {
      props: { customWidth: "200px", customHeight: "100px" }
    });
    expect(wrapper.attributes("style")).toContain("width: 200px");
    expect(wrapper.attributes("style")).toContain("height: 100px");
  });
});

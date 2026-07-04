import { ref, watch, onMounted } from "vue";

/**
 * 数字递增动效 composable
 *
 * 配合 CSS @property --num + number-count-up keyframe 使用，
 * 在指定时长内将数字从 0 递增到目标值。
 *
 * @example
 * ```vue
 * <span :style="countStyle">{{ displayValue }}</span>
 * ```
 */
export function useCountUp(target: number | (() => number), durationMs = 1000) {
  const displayValue = ref(0);
  const isAnimating = ref(false);

  const countStyle = {
    "--target-num": typeof target === "function" ? target() : target,
    animation: `number-count-up ${durationMs}ms var(--ease-decelerate) forwards`
  } as Record<string, string>;

  function animate() {
    displayValue.value = 0;
    isAnimating.value = true;

    const end = typeof target === "function" ? target() : target;
    const startTime = performance.now();

    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / durationMs, 1);
      // ease-decelerate 模拟: 快开始慢结束
      const eased = 1 - Math.pow(1 - progress, 2);
      displayValue.value = Math.round(eased * end);

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        displayValue.value = end;
        isAnimating.value = false;
      }
    }

    requestAnimationFrame(tick);
  }

  onMounted(() => {
    animate();
  });

  watch(
    () => (typeof target === "function" ? target() : target),
    () => {
      animate();
    }
  );

  return { displayValue, isAnimating, countStyle, animate };
}

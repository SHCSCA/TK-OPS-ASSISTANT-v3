import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useShellUiStore } from "@/stores/shell-ui";

export function useMotion() {
  const shellUiStore = useShellUiStore();
  const { reducedMotion } = storeToRefs(shellUiStore);

  const isMotionEnabled = computed(() => !reducedMotion.value);

  const getTransitionDuration = (durationToken: string) => {
    return isMotionEnabled.value ? `var(${durationToken})` : "1ms";
  };

  const getAnimationDuration = (duration: string) => {
    return isMotionEnabled.value ? duration : "1ms";
  };

  return {
    reducedMotion,
    isMotionEnabled,
    getTransitionDuration,
    getAnimationDuration
  };
}

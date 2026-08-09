import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  watch
} from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  LEGACY_MIGRATION_QUERY_KEY,
  resolveLegacyMigrationMessage
} from "@/app/router";
import { consoleAccountContextLogger } from "@/app/account-context";

export function useWorkspaceOverlays() {
  const route = useRoute();
  const router = useRouter();
  const accountDetailOpen = ref(false);
  const migrationMessage = computed(() =>
    resolveLegacyMigrationMessage(
      route.query[LEGACY_MIGRATION_QUERY_KEY]
    )
  );

  watch(
    () => route.path,
    () => {
      accountDetailOpen.value = false;
    }
  );

  onMounted(() => {
    window.addEventListener("keydown", handleKeydown);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("keydown", handleKeydown);
  });

  async function dismissMigrationNotice(): Promise<void> {
    const query = { ...route.query };
    delete query[LEGACY_MIGRATION_QUERY_KEY];
    try {
      await router.replace({
        path: route.path,
        query,
        hash: route.hash
      });
    } catch (error) {
      consoleAccountContextLogger.error(
        "[account-shell] 关闭旧入口迁移提示失败",
        error
      );
    }
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape" && accountDetailOpen.value) {
      accountDetailOpen.value = false;
    }
  }

  return {
    accountDetailOpen,
    dismissMigrationNotice,
    migrationMessage
  };
}

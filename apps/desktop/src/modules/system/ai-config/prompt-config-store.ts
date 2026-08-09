import { defineStore } from "pinia";

import {
  activatePromptVersion,
  createPromptProfile,
  createPromptVersion,
  getPromptVersion,
  listPromptProfiles
} from "@/app/runtime-client/ai-system";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import type {
  AICapabilityKey,
  PromptProfileDto,
  PromptVersionDto
} from "@/types/runtime/ai-system";

import {
  createAIOperationKey,
  logAIConfigError,
  pageStateFromError,
  parseJsonObject,
  prettyJson,
  toAIConfigUiError
} from "./ai-config-helpers";
import type {
  AIConfigUiError,
  AIPageState,
  PromptEditorDraft
} from "./ai-config-types";

type PromptConfigState = {
  profiles: PromptProfileDto[];
  totalKnown: number | null;
  selectedProfileKey: string | null;
  selectedVersion: number | null;
  bodyByVersion: Record<string, PromptVersionDto>;
  editorState: "closed" | "summary" | "loading_body" | "view" | "edit";
  draft: PromptEditorDraft | null;
  dirty: boolean;
  search: string;
  capabilityFilter: AICapabilityKey | "";
  state: AIPageState;
  error: AIConfigUiError | null;
  feedback: string | null;
  busyKey: string | null;
};

let loadController: AbortController | null = null;
let detailController: AbortController | null = null;
let loadSequence = 0;
let detailSequence = 0;

export const usePromptConfigStore = defineStore("p0-ai-prompt-config", {
  state: (): PromptConfigState => ({
    profiles: [],
    totalKnown: null,
    selectedProfileKey: null,
    selectedVersion: null,
    bodyByVersion: Object.create(null) as Record<string, PromptVersionDto>,
    editorState: "closed",
    draft: null,
    dirty: false,
    search: "",
    capabilityFilter: "",
    state: "idle",
    error: null,
    feedback: null,
    busyKey: null
  }),
  getters: {
    selectedProfile(state): PromptProfileDto | null {
      return state.profiles.find(
        (profile) => profile.profileKey === state.selectedProfileKey
      ) ?? null;
    },
    selectedBody(state): PromptVersionDto | null {
      if (!state.selectedProfileKey || state.selectedVersion === null) return null;
      return state.bodyByVersion[
        versionCacheKey(state.selectedProfileKey, state.selectedVersion)
      ] ?? null;
    },
    filteredProfiles(state): PromptProfileDto[] {
      const search = state.search.trim().toLocaleLowerCase();
      return state.profiles.filter((profile) => {
        const matchesCapability = !state.capabilityFilter
          || profile.capabilityKey === state.capabilityFilter;
        const matchesSearch = !search
          || profile.name.toLocaleLowerCase().includes(search)
          || profile.profileKey.toLocaleLowerCase().includes(search);
        return matchesCapability && matchesSearch;
      });
    },
    hasFilters(state): boolean {
      return Boolean(state.search.trim() || state.capabilityFilter);
    }
  },
  actions: {
    async load(): Promise<void> {
      const sequence = ++loadSequence;
      loadController?.abort();
      loadController = new AbortController();
      if (!this.profiles.length) this.state = "loading";
      this.error = null;
      try {
        const result = await listPromptProfiles(
          { limit: 200 },
          { signal: loadController.signal }
        );
        if (sequence !== loadSequence) return;
        this.profiles = result.data.items;
        this.totalKnown = result.data.totalKnown;
        if (
          this.selectedProfileKey
          && !this.profiles.some(
            (profile) => profile.profileKey === this.selectedProfileKey
          )
        ) {
          this.closeEditor();
        }
        this.recomputeState();
      } catch (error) {
        if (isRuntimeRequestAborted(error) || sequence !== loadSequence) return;
        this.fail(error, "Prompt 模板列表加载失败。");
      } finally {
        if (sequence === loadSequence) loadController = null;
      }
    },

    selectProfile(profileKey: string): void {
      const profile = this.profiles.find((item) => item.profileKey === profileKey);
      if (!profile) return;
      detailController?.abort();
      this.selectedProfileKey = profileKey;
      this.selectedVersion = profile.activeVersion
        ?? profile.versions.at(-1)?.version
        ?? null;
      this.editorState = "summary";
      this.draft = null;
      this.dirty = false;
      this.error = null;
    },

    selectVersion(version: number): void {
      this.selectedVersion = version;
      this.editorState = "summary";
      this.draft = null;
      this.dirty = false;
    },

    async openSelectedBody(): Promise<void> {
      const profileKey = this.selectedProfileKey;
      const version = this.selectedVersion;
      if (!profileKey || version === null) return;
      const cached = this.bodyByVersion[versionCacheKey(profileKey, version)];
      if (cached) {
        this.editorState = "view";
        return;
      }
      const sequence = ++detailSequence;
      detailController?.abort();
      detailController = new AbortController();
      this.editorState = "loading_body";
      this.error = null;
      try {
        const result = await getPromptVersion(profileKey, version, {
          signal: detailController.signal
        });
        if (
          sequence !== detailSequence
          || this.selectedProfileKey !== profileKey
          || this.selectedVersion !== version
        ) {
          return;
        }
        this.bodyByVersion[versionCacheKey(profileKey, version)] = result.data;
        this.editorState = "view";
      } catch (error) {
        if (isRuntimeRequestAborted(error) || sequence !== detailSequence) return;
        this.fail(error, "Prompt 正文加载失败。");
      } finally {
        if (sequence === detailSequence) detailController = null;
      }
    },

    beginCreateProfile(): void {
      detailController?.abort();
      this.selectedProfileKey = null;
      this.selectedVersion = null;
      this.draft = emptyPromptDraft();
      this.editorState = "edit";
      this.dirty = false;
      this.error = null;
    },

    beginCreateVersion(): void {
      const body = this.selectedBody;
      if (!body) return;
      this.draft = {
        mode: "create_version",
        profileKey: body.profileKey,
        capabilityKey: body.capabilityKey,
        name: body.name,
        systemPrompt: body.systemPrompt,
        taskTemplate: body.taskTemplate,
        variablesSchema: prettyJson(body.variablesSchema),
        outputSchema: prettyJson(body.outputSchema),
        visualStylePrefix: body.visualStylePrefix,
        safetyConstraints: prettyJson(body.safetyConstraints),
        createdFromVersion: body.version
      };
      this.editorState = "edit";
      this.dirty = false;
    },

    updateDraft<K extends keyof PromptEditorDraft>(
      field: K,
      value: PromptEditorDraft[K]
    ): void {
      if (!this.draft) return;
      this.draft[field] = value;
      this.dirty = true;
    },

    async saveDraft(): Promise<boolean> {
      const draft = this.draft;
      if (!draft) return true;
      let payload;
      try {
        payload = {
          name: draft.name.trim(),
          systemPrompt: draft.systemPrompt,
          taskTemplate: draft.taskTemplate,
          variablesSchema: parseJsonObject(
            draft.variablesSchema,
            "变量 Schema"
          ),
          outputSchema: parseJsonObject(draft.outputSchema, "输出 Schema"),
          visualStylePrefix: draft.visualStylePrefix,
          safetyConstraints: parseJsonObject(
            draft.safetyConstraints,
            "安全约束"
          )
        };
      } catch (error) {
        this.fail(error, "Prompt 配置格式无效。");
        return false;
      }
      return this.runMutation("prompt-save", async () => {
        if (draft.mode === "create_profile") {
          const result = await createPromptProfile(
            {
              ...payload,
              profileKey: draft.profileKey.trim(),
              capabilityKey: draft.capabilityKey
            },
            {
              idempotencyKey: createAIOperationKey(
                "prompt-profile-create",
                draft.profileKey.trim()
              )
            }
          );
          this.selectedProfileKey = result.data.profileKey;
          this.selectedVersion = result.data.versions.at(-1)?.version ?? null;
        } else {
          const profile = this.selectedProfile;
          if (!profile) throw new Error("Prompt 摘要已失效，请重新打开。");
          const result = await createPromptVersion(
            profile.profileKey,
            { ...payload, createdFromVersion: draft.createdFromVersion },
            {
              expectedRevision: profile.revision,
              idempotencyKey: createAIOperationKey(
                "prompt-version-create",
                profile.profileKey
              )
            }
          );
          this.selectedVersion = result.data.version;
          this.bodyByVersion[
            versionCacheKey(profile.profileKey, result.data.version)
          ] = result.data;
        }
        this.dirty = false;
        this.feedback = "已创建新的 Prompt 版本，原激活版本未被改写。";
        await this.load();
        this.editorState =
          draft.mode === "create_profile" || this.selectedVersion === null
            ? "summary"
            : "view";
      });
    },

    async activateSelectedVersion(): Promise<boolean> {
      const profile = this.selectedProfile;
      const version = this.selectedVersion;
      if (!profile || version === null) return false;
      return this.runMutation("prompt-activate", async () => {
        await activatePromptVersion(profile.profileKey, version, {
          expectedRevision: profile.revision,
          idempotencyKey: createAIOperationKey(
            "prompt-version-activate",
            profile.profileKey
          )
        });
        this.feedback = `Prompt 版本 v${version} 已激活。`;
        await this.load();
        delete this.bodyByVersion[versionCacheKey(profile.profileKey, version)];
        this.editorState = "summary";
      });
    },

    discardDraft(): void {
      this.dirty = false;
      this.draft = null;
      this.editorState = this.selectedProfileKey ? "summary" : "closed";
    },

    closeEditor(): void {
      detailController?.abort();
      this.selectedProfileKey = null;
      this.selectedVersion = null;
      this.draft = null;
      this.dirty = false;
      this.editorState = "closed";
    },

    clearFilters(): void {
      this.search = "";
      this.capabilityFilter = "";
      this.recomputeState();
    },

    clearFeedback(): void {
      this.feedback = null;
      this.error = null;
      this.recomputeState();
    },

    recomputeState(): void {
      if (this.error) this.state = pageStateFromError(this.error);
      else if (!this.profiles.length) this.state = "first_use";
      else if (!this.filteredProfiles.length && this.hasFilters) {
        this.state = "filtered_empty";
      } else {
        this.state = "ready";
      }
    },

    async runMutation(
      busyKey: string,
      operation: () => Promise<void>
    ): Promise<boolean> {
      this.busyKey = busyKey;
      this.error = null;
      try {
        await operation();
        return true;
      } catch (error) {
        this.fail(error, "Prompt 操作失败，请检查内容后重试。");
        return false;
      } finally {
        if (this.busyKey === busyKey) this.busyKey = null;
      }
    },

    fail(error: unknown, fallback: string): void {
      logAIConfigError(fallback, error);
      this.error = toAIConfigUiError(error, fallback);
      this.state = pageStateFromError(this.error);
    }
  }
});

function emptyPromptDraft(): PromptEditorDraft {
  return {
    mode: "create_profile",
    profileKey: "",
    capabilityKey: "script_generation",
    name: "",
    systemPrompt: "",
    taskTemplate: "",
    variablesSchema: "{}",
    outputSchema: "{}",
    visualStylePrefix: "",
    safetyConstraints: "{}",
    createdFromVersion: 0
  };
}

function versionCacheKey(profileKey: string, version: number): string {
  return `${profileKey}@${version}`;
}

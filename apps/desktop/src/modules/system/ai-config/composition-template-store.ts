import { defineStore } from "pinia";

import {
  activateCompositionTemplateVersion,
  createCompositionTemplate,
  createCompositionTemplateVersion,
  getCompositionTemplateVersion,
  listCompositionTemplates,
  validateCompositionTemplateVersion
} from "@/app/runtime-client/ai-system";
import { isRuntimeRequestAborted } from "@/app/runtime-client/core";
import type {
  CompositionTemplateDto,
  CompositionTemplateValidationDto,
  CompositionTemplateVersionDto
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
  CompositionTemplateEditorDraft
} from "./ai-config-types";

type CompositionTemplateState = {
  templates: CompositionTemplateDto[];
  selectedTemplateKey: string | null;
  selectedVersion: number | null;
  bodyByVersion: Record<string, CompositionTemplateVersionDto>;
  validationByVersion: Record<string, CompositionTemplateValidationDto>;
  editorState: "closed" | "summary" | "loading_body" | "view" | "edit";
  draft: CompositionTemplateEditorDraft | null;
  dirty: boolean;
  search: string;
  state: AIPageState;
  error: AIConfigUiError | null;
  feedback: string | null;
  busyKey: string | null;
};

let loadController: AbortController | null = null;
let detailController: AbortController | null = null;
let loadSequence = 0;
let detailSequence = 0;

export const useCompositionTemplateStore = defineStore(
  "p0-ai-composition-template",
  {
    state: (): CompositionTemplateState => ({
      templates: [],
      selectedTemplateKey: null,
      selectedVersion: null,
      bodyByVersion: Object.create(null) as Record<
        string,
        CompositionTemplateVersionDto
      >,
      validationByVersion: Object.create(null) as Record<
        string,
        CompositionTemplateValidationDto
      >,
      editorState: "closed",
      draft: null,
      dirty: false,
      search: "",
      state: "idle",
      error: null,
      feedback: null,
      busyKey: null
    }),
    getters: {
      selectedTemplate(state): CompositionTemplateDto | null {
        return state.templates.find(
          (template) => template.templateKey === state.selectedTemplateKey
        ) ?? null;
      },
      selectedBody(state): CompositionTemplateVersionDto | null {
        if (!state.selectedTemplateKey || state.selectedVersion === null) {
          return null;
        }
        return state.bodyByVersion[
          versionCacheKey(state.selectedTemplateKey, state.selectedVersion)
        ] ?? null;
      },
      selectedValidation(state): CompositionTemplateValidationDto | null {
        if (!state.selectedTemplateKey || state.selectedVersion === null) {
          return null;
        }
        return state.validationByVersion[
          versionCacheKey(state.selectedTemplateKey, state.selectedVersion)
        ] ?? null;
      },
      filteredTemplates(state): CompositionTemplateDto[] {
        const search = state.search.trim().toLocaleLowerCase();
        if (!search) return state.templates;
        return state.templates.filter(
          (template) =>
            template.name.toLocaleLowerCase().includes(search)
            || template.templateKey.toLocaleLowerCase().includes(search)
        );
      },
      hasFilters(state): boolean {
        return Boolean(state.search.trim());
      }
    },
    actions: {
      async load(): Promise<void> {
        const sequence = ++loadSequence;
        loadController?.abort();
        loadController = new AbortController();
        if (!this.templates.length) this.state = "loading";
        this.error = null;
        try {
          const result = await listCompositionTemplates(
            { limit: 200 },
            { signal: loadController.signal }
          );
          if (sequence !== loadSequence) return;
          this.templates = result.data.items;
          if (
            this.selectedTemplateKey
            && !this.templates.some(
              (item) => item.templateKey === this.selectedTemplateKey
            )
          ) {
            this.closeEditor();
          }
          this.recomputeState();
        } catch (error) {
          if (isRuntimeRequestAborted(error) || sequence !== loadSequence) return;
          this.fail(error, "合成模板列表加载失败。");
        } finally {
          if (sequence === loadSequence) loadController = null;
        }
      },

      selectTemplate(templateKey: string): void {
        const template = this.templates.find(
          (item) => item.templateKey === templateKey
        );
        if (!template) return;
        detailController?.abort();
        this.selectedTemplateKey = templateKey;
        this.selectedVersion = template.activeVersion
          ?? template.versions.at(-1)?.version
          ?? null;
        this.editorState = "summary";
        this.draft = null;
        this.dirty = false;
      },

      selectVersion(version: number): void {
        this.selectedVersion = version;
        this.editorState = "summary";
        this.draft = null;
        this.dirty = false;
      },

      async openSelectedBody(): Promise<void> {
        const templateKey = this.selectedTemplateKey;
        const version = this.selectedVersion;
        if (!templateKey || version === null) return;
        if (this.bodyByVersion[versionCacheKey(templateKey, version)]) {
          this.editorState = "view";
          return;
        }
        const sequence = ++detailSequence;
        detailController?.abort();
        detailController = new AbortController();
        this.editorState = "loading_body";
        this.error = null;
        try {
          const result = await getCompositionTemplateVersion(
            templateKey,
            version,
            { signal: detailController.signal }
          );
          if (
            sequence !== detailSequence
            || this.selectedTemplateKey !== templateKey
            || this.selectedVersion !== version
          ) {
            return;
          }
          this.bodyByVersion[versionCacheKey(templateKey, version)] = result.data;
          this.editorState = "view";
        } catch (error) {
          if (isRuntimeRequestAborted(error) || sequence !== detailSequence) return;
          this.fail(error, "合成模板正文加载失败。");
        } finally {
          if (sequence === detailSequence) detailController = null;
        }
      },

      beginCreateTemplate(): void {
        detailController?.abort();
        this.selectedTemplateKey = null;
        this.selectedVersion = null;
        this.draft = emptyTemplateDraft();
        this.editorState = "edit";
        this.dirty = false;
      },

      beginCreateVersion(): void {
        const body = this.selectedBody;
        if (!body) return;
        this.draft = {
          mode: "create_version",
          templateKey: body.templateKey,
          templateType: body.templateType,
          name: body.name,
          aspectRatios: body.aspectRatios.join(", "),
          parameterSchema: prettyJson(body.parameterSchema),
          compositionSpecTemplate: prettyJson(body.compositionSpecTemplate),
          compatibleCapabilities: prettyJson(body.compatibleCapabilities),
          previewAssetRef: body.previewAssetRef ?? "",
          createdFromVersion: body.version
        };
        this.editorState = "edit";
        this.dirty = false;
      },

      updateDraft<K extends keyof CompositionTemplateEditorDraft>(
        field: K,
        value: CompositionTemplateEditorDraft[K]
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
            aspectRatios: draft.aspectRatios
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
            parameterSchema: parseJsonObject(
              draft.parameterSchema,
              "参数 Schema"
            ),
            compositionSpecTemplate: parseJsonObject(
              draft.compositionSpecTemplate,
              "CompositionSpec 模板"
            ),
            compatibleCapabilities: parseJsonObject(
              draft.compatibleCapabilities,
              "兼容能力"
            ),
            previewAssetRef: draft.previewAssetRef.trim() || null
          };
        } catch (error) {
          this.fail(error, "合成模板配置格式无效。");
          return false;
        }
        return this.runMutation("composition-save", async () => {
          if (draft.mode === "create_profile") {
            const result = await createCompositionTemplate(
              {
                ...payload,
                templateKey: draft.templateKey.trim(),
                templateType: draft.templateType
              },
              {
                idempotencyKey: createAIOperationKey(
                  "composition-template-create",
                  draft.templateKey.trim()
                )
              }
            );
            this.selectedTemplateKey = result.data.templateKey;
            this.selectedVersion = result.data.versions.at(-1)?.version ?? null;
          } else {
            const template = this.selectedTemplate;
            if (!template) throw new Error("模板摘要已失效，请重新打开。");
            const result = await createCompositionTemplateVersion(
              template.templateKey,
              { ...payload, createdFromVersion: draft.createdFromVersion },
              {
                expectedRevision: template.revision,
                idempotencyKey: createAIOperationKey(
                  "composition-version-create",
                  template.templateKey
                )
              }
            );
            this.selectedVersion = result.data.version;
            this.bodyByVersion[
              versionCacheKey(template.templateKey, result.data.version)
            ] = result.data;
          }
          this.dirty = false;
          this.feedback = "已创建新的合成模板版本，原激活版本保持不变。";
          await this.load();
          this.editorState =
            draft.mode === "create_profile" || this.selectedVersion === null
              ? "summary"
              : "view";
        });
      },

      async validateSelectedVersion(): Promise<boolean> {
        const template = this.selectedTemplate;
        const version = this.selectedVersion;
        if (!template || version === null) return false;
        return this.runMutation("composition-validate", async () => {
          const result = await validateCompositionTemplateVersion(
            template.templateKey,
            version,
            {
              idempotencyKey: createAIOperationKey(
                "composition-version-validate",
                template.templateKey
              )
            }
          );
          this.validationByVersion[
            versionCacheKey(template.templateKey, version)
          ] = result.data;
          this.feedback =
            result.data.validationStatus === "valid"
              ? "模板 Schema、能力和预览引用验证通过。"
              : "模板验证未通过，请根据问题修复新版本。";
        });
      },

      async activateSelectedVersion(): Promise<boolean> {
        const template = this.selectedTemplate;
        const version = this.selectedVersion;
        if (!template || version === null) return false;
        return this.runMutation("composition-activate", async () => {
          await activateCompositionTemplateVersion(
            template.templateKey,
            version,
            {
              expectedRevision: template.revision,
              idempotencyKey: createAIOperationKey(
                "composition-version-activate",
                template.templateKey
              )
            }
          );
          this.feedback = `合成模板版本 v${version} 已激活。`;
          await this.load();
          delete this.bodyByVersion[
            versionCacheKey(template.templateKey, version)
          ];
          this.editorState = "summary";
        });
      },

      discardDraft(): void {
        this.dirty = false;
        this.draft = null;
        this.editorState = this.selectedTemplateKey ? "summary" : "closed";
      },

      closeEditor(): void {
        detailController?.abort();
        this.selectedTemplateKey = null;
        this.selectedVersion = null;
        this.draft = null;
        this.dirty = false;
        this.editorState = "closed";
      },

      clearFilters(): void {
        this.search = "";
        this.recomputeState();
      },

      clearFeedback(): void {
        this.feedback = null;
        this.error = null;
        this.recomputeState();
      },

      recomputeState(): void {
        if (this.error) this.state = pageStateFromError(this.error);
        else if (!this.templates.length) this.state = "first_use";
        else if (!this.filteredTemplates.length && this.hasFilters) {
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
          this.fail(error, "合成模板操作失败，请检查内容后重试。");
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
  }
);

function emptyTemplateDraft(): CompositionTemplateEditorDraft {
  return {
    mode: "create_profile",
    templateKey: "",
    templateType: "mixed_media",
    name: "",
    aspectRatios: "9:16",
    parameterSchema: "{}",
    compositionSpecTemplate: "{}",
    compatibleCapabilities: "{}",
    previewAssetRef: "",
    createdFromVersion: 0
  };
}

function versionCacheKey(templateKey: string, version: number): string {
  return `${templateKey}@${version}`;
}

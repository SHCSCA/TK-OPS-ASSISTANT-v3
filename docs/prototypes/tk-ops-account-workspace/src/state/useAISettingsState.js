import { useAIConfigurationState } from "./ai-settings/useAIConfigurationState.js";
import { useProviderProfilesState } from "./ai-settings/useProviderProfilesState.js";

export function useAISettingsState(notify) {
  const providerState = useProviderProfilesState(notify);
  const configurationState = useAIConfigurationState(notify);

  function saveProvider({ provider, models }) {
    const modelIds = configurationState.addModels(provider.id, models);
    return providerState.addProvider({ ...provider, modelIds });
  }

  return {
    ...configurationState,
    ...providerState,
    saveProvider,
  };
}

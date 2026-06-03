import type { ProfileCapability, ProfileKind } from "./types";

export interface ProviderPreset {
  id: string;
  label: string;
  kind: ProfileKind;
  base_url: string;
  model: string;
  api_key_ref: string | null;
  capabilities: ProfileCapability[];
}

export const providerPresets: ProviderPreset[] = [
  {
    id: "openai",
    label: "OpenAI",
    kind: "openai_compatible",
    base_url: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
    api_key_ref: "OPENAI_API_KEY",
    capabilities: ["chat"],
  },
  {
    id: "anthropic",
    label: "Anthropic",
    kind: "openai_compatible",
    base_url: "https://api.anthropic.com/v1",
    model: "claude-3-5-sonnet-latest",
    api_key_ref: "ANTHROPIC_API_KEY",
    capabilities: ["chat"],
  },
  {
    id: "gemini",
    label: "Gemini",
    kind: "openai_compatible",
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai",
    model: "gemini-2.0-flash",
    api_key_ref: "GEMINI_API_KEY",
    capabilities: ["chat"],
  },
  {
    id: "ollama",
    label: "Ollama",
    kind: "ollama",
    // host.docker.internal resolves to the host machine from within the backend container
    base_url: "http://host.docker.internal:11434/v1",
    model: "llama3.1",
    api_key_ref: null,
    capabilities: ["chat"],
  },
  {
    id: "lmstudio",
    label: "LM Studio",
    kind: "openai_compatible",
    // host.docker.internal resolves to the host machine from within the backend container
    base_url: "http://host.docker.internal:1234/v1",
    model: "local-model",
    api_key_ref: null,
    capabilities: ["chat"],
  },
  {
    id: "koboldcpp",
    label: "KoboldCpp",
    kind: "koboldcpp",
    // host.docker.internal resolves to the host machine from within the backend container
    base_url: "http://host.docker.internal:5001/v1",
    model: "",
    api_key_ref: null,
    capabilities: ["chat"],
  },
];

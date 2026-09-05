import { invoke, isTauri } from '@tauri-apps/api/core';
export const isNative = isTauri();
export function nativeCall<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  if (!isNative)
    return Promise.reject(new Error('This operation requires the native ALICE application.'));
  return invoke<T>(command, args);
}
export interface RuntimeConfig {
  transport_mode: 'mock' | 'remote';
  biometric_mode: 'mock' | 'arcface';
  llm_model: string;
  ollama_url: string;
  biometric_url: string;
  admin_configured: boolean;
}
export async function runtimeConfig(): Promise<RuntimeConfig> {
  if (isNative) return nativeCall('runtime_config');
  return {
    transport_mode: import.meta.env.VITE_ALICE_PREVIEW_MODE === 'remote' ? 'remote' : 'mock',
    biometric_mode: 'mock',
    llm_model: '',
    ollama_url: 'http://127.0.0.1:11434',
    biometric_url: 'http://127.0.0.1:8765',
    admin_configured: false,
  };
}

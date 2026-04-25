import { useState, useMemo, useCallback } from 'react';
import type React from 'react';
import type { ParsedApiError } from '../../api/error';
import { getParsedApiError } from '../../api/error';
import { ApiErrorAlert, EyeToggleIcon } from '../common';
import { systemConfigApi } from '../../api/systemConfig';

/** Well-known channel presets for quick-add dropdown. */
const CHANNEL_PRESETS: Record<string, { label: string; baseUrl: string; placeholder: string }> = {
  openai: {
    label: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    placeholder: 'gpt-4o-mini,gpt-4.1-mini',
  },
  anthropic: {
    label: 'Anthropic',
    baseUrl: 'https://api.anthropic.com/v1',
    placeholder: 'claude-3-5-sonnet-latest,claude-3-5-haiku-latest',
  },
  openrouter: {
    label: 'OpenRouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    placeholder: 'gpt-4o,claude-3.5-sonnet',
  },
  gemini: {
    label: 'Gemini',
    baseUrl: '',
    placeholder: 'gemini/gemini-2.5-flash',
  },
  custom: {
    label: '사용자 지정 채널',
    baseUrl: '',
    placeholder: 'model-name-1,model-name-2',
  },
};

interface ChannelConfig {
  /** Channel identifier (used in env var prefix). */
  name: string;
  baseUrl: string;
  apiKey: string;
  models: string;
}

interface LLMChannelEditorProps {
  /** All config items from the server (to read existing channel vars). */
  items: Array<{ key: string; value: string }>;
  /** Current config version for API calls. */
  configVersion: string;
  /** Mask token for secrets. */
  maskToken: string;
  /** Called after successful save to reload config. */
  onSaved: () => void;
  /** Disable interactions while parent is busy. */
  disabled?: boolean;
}

/** Extract `LLM_{NAME}_*` env vars from items and group them by channel. */
function parseChannelsFromItems(items: Array<{ key: string; value: string }>): ChannelConfig[] {
  const itemMap = new Map(items.map((i) => [i.key, i.value]));
  const channelNames = (itemMap.get('LLM_CHANNELS') || '')
    .split(',')
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);

  if (channelNames.length === 0) {
    return [];
  }

  return channelNames.map((name) => ({
    name: name.toLowerCase(),
    baseUrl: itemMap.get(`LLM_${name}_BASE_URL`) || '',
    apiKey: itemMap.get(`LLM_${name}_API_KEY`) || itemMap.get(`LLM_${name}_API_KEYS`) || '',
    models: itemMap.get(`LLM_${name}_MODELS`) || '',
  }));
}

/** Build env var update items from channel list. */
function channelsToUpdateItems(
  channels: ChannelConfig[],
  previousChannelNames: string[],
): Array<{ key: string; value: string }> {
  const updates: Array<{ key: string; value: string }> = [];
  const activeNames = channels.map((c) => c.name.toUpperCase());

  // LLM_CHANNELS
  updates.push({ key: 'LLM_CHANNELS', value: channels.map((c) => c.name).join(',') });

  // Per-channel vars
  for (const ch of channels) {
    const prefix = `LLM_${ch.name.toUpperCase()}`;
    updates.push({ key: `${prefix}_BASE_URL`, value: ch.baseUrl });
    // Use API_KEY for single key, API_KEYS for comma-separated multi-key
    const isMultiKey = ch.apiKey.includes(',');
    updates.push({ key: `${prefix}_API_KEY${isMultiKey ? 'S' : ''}`, value: ch.apiKey });
    // Clear the other key variant
    updates.push({ key: `${prefix}_API_KEY${isMultiKey ? '' : 'S'}`, value: '' });
    updates.push({ key: `${prefix}_MODELS`, value: ch.models });
  }

  // Clear removed channel vars
  for (const oldName of previousChannelNames) {
    const upper = oldName.toUpperCase();
    if (!activeNames.includes(upper)) {
      const prefix = `LLM_${upper}`;
      updates.push({ key: `${prefix}_BASE_URL`, value: '' });
      updates.push({ key: `${prefix}_API_KEY`, value: '' });
      updates.push({ key: `${prefix}_API_KEYS`, value: '' });
      updates.push({ key: `${prefix}_MODELS`, value: '' });
    }
  }

  return updates;
}

export const LLMChannelEditor: React.FC<LLMChannelEditorProps> = ({
  items,
  configVersion,
  maskToken,
  onSaved,
  disabled = false,
}) => {
  const initialChannels = useMemo(() => parseChannelsFromItems(items), [items]);
  const initialNames = useMemo(
    () => initialChannels.map((c) => c.name),
    [initialChannels],
  );

  const [channels, setChannels] = useState<ChannelConfig[]>(initialChannels);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<
    { type: 'success'; text: string } | { type: 'error'; error: ParsedApiError } | null
  >(null);
  const [visibleKeys, setVisibleKeys] = useState<Record<number, boolean>>({});
  const [isCollapsed, setIsCollapsed] = useState(initialChannels.length === 0);
  const [addPreset, setAddPreset] = useState('openrouter');

  // Detect if user has unsaved channel changes
  const hasChanges = useMemo(() => {
    if (channels.length !== initialChannels.length) return true;
    return channels.some((ch, idx) => {
      const init = initialChannels[idx];
      if (!init) return true;
      return (
        ch.name !== init.name ||
        ch.baseUrl !== init.baseUrl ||
        ch.apiKey !== init.apiKey ||
        ch.models !== init.models
      );
    });
  }, [channels, initialChannels]);

  const updateChannel = useCallback((index: number, field: keyof ChannelConfig, value: string) => {
    setChannels((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }, []);

  const removeChannel = useCallback((index: number) => {
    setChannels((prev) => prev.filter((_, i) => i !== index));
    setVisibleKeys((prev) => {
      const next = { ...prev };
      delete next[index];
      return next;
    });
  }, []);

  const addChannel = useCallback(() => {
    const preset = CHANNEL_PRESETS[addPreset] || CHANNEL_PRESETS.custom;
    // Determine a unique name
    const baseName = addPreset === 'custom' ? 'custom' : addPreset;
    const existingNames = new Set(channels.map((c) => c.name));
    let name = baseName;
    let counter = 2;
    while (existingNames.has(name)) {
      name = `${baseName}${counter}`;
      counter++;
    }

    setChannels((prev) => [
      ...prev,
      { name, baseUrl: preset.baseUrl, apiKey: '', models: '' },
    ]);
    setIsCollapsed(false);
  }, [addPreset, channels]);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setSaveMessage(null);

    try {
      const updateItems = channelsToUpdateItems(channels, initialNames);
      await systemConfigApi.update({
        configVersion,
        maskToken,
        reloadNow: true,
        items: updateItems,
      });
      setSaveMessage({ type: 'success', text: '채널 설정이 저장되었습니다' });
      onSaved();
    } catch (error: unknown) {
      setSaveMessage({ type: 'error', error: getParsedApiError(error) });
    } finally {
      setIsSaving(false);
    }
  }, [channels, configVersion, initialNames, maskToken, onSaved]);

  const toggleKeyVisibility = useCallback((index: number) => {
    setVisibleKeys((prev) => ({ ...prev, [index]: !prev[index] }));
  }, []);

  const busy = disabled || isSaving;

  return (
    <div className="rounded-xl border border-cyan/20 bg-elevated/50 p-4">
      <button
        type="button"
        className="flex w-full items-center justify-between text-left"
        onClick={() => setIsCollapsed((prev) => !prev)}
      >
        <div>
          <h3 className="text-sm font-semibold text-white">LLM 채널 설정</h3>
          <p className="mt-0.5 text-xs text-muted">
            {channels.length > 0
              ? `${channels.length}개 채널 설정됨: ${channels.map((c) => c.name).join(', ')}`
              : (
                '여러 모델 플랫폼을 함께 사용할 때 설정하세요. '
                + '단일 모델만 사용하면 건너뛸 수 있습니다.'
              )}
          </p>
        </div>
        <span className="text-xs text-muted">{isCollapsed ? '▶ 펼치기' : '▼ 접기'}</span>
      </button>

      {!isCollapsed && (
        <div className="mt-4 space-y-3">
          {channels.map((channel, index) => (
            <div
              key={`${channel.name}-${index}`}
              className="rounded-lg border border-white/8 bg-card/40 p-3 space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-accent">
                    {CHANNEL_PRESETS[channel.name]?.label || channel.name}
                  </span>
                </div>
                <button
                  type="button"
                  className="text-xs text-red-400 hover:text-red-300 disabled:opacity-40"
                  disabled={busy}
                  onClick={() => removeChannel(index)}
                >
                  삭제
                </button>
              </div>

              {/* Channel name */}
              <div>
                <label className="mb-1 block text-xs text-secondary">채널 이름</label>
                <input
                  type="text"
                  className="input-terminal w-full"
                  value={channel.name}
                  disabled={busy}
                  onChange={(e) => {
                    updateChannel(index, 'name', e.target.value.replace(/[^a-zA-Z0-9_]/g, '').toLowerCase());
                  }}
                  placeholder="예: openrouter, openai"
                />
              </div>

              {/* Base URL */}
              <div>
                <label className="mb-1 block text-xs text-secondary">API 주소(Base URL)</label>
                <input
                  type="text"
                  className="input-terminal w-full"
                  value={channel.baseUrl}
                  disabled={busy}
                  onChange={(e) => updateChannel(index, 'baseUrl', e.target.value)}
                  placeholder="https://api.example.com/v1 (Gemini는 비워 둘 수 있음)"
                />
              </div>

              {/* API Key */}
              <div>
                <label className="mb-1 block text-xs text-secondary">API Key(여러 개는 쉼표로 구분)</label>
                <div className="flex items-center gap-2">
                  <input
                    type={visibleKeys[index] ? 'text' : 'password'}
                    className="input-terminal flex-1"
                    value={channel.apiKey}
                    disabled={busy}
                    onChange={(e) => updateChannel(index, 'apiKey', e.target.value)}
                    placeholder="sk-xxxxxxxxxxxxxxxx"
                  />
                  <button
                    type="button"
                    className="btn-secondary !p-2"
                    onClick={() => toggleKeyVisibility(index)}
                    title={visibleKeys[index] ? '숨기기' : '표시'}
                  >
                    <EyeToggleIcon visible={!!visibleKeys[index]} />
                  </button>
                </div>
              </div>

              {/* Models */}
              <div>
                <label className="mb-1 block text-xs text-secondary">모델 목록(쉼표로 구분)</label>
                <input
                  type="text"
                  className="input-terminal w-full"
                  value={channel.models}
                  disabled={busy}
                  onChange={(e) => updateChannel(index, 'models', e.target.value)}
                  placeholder={CHANNEL_PRESETS[channel.name]?.placeholder || 'model-1,model-2'}
                />
                <p className="mt-1 text-[11px] text-muted">
                  Base URL이 있는 채널은 openai/ 접두사를 붙이지 않아도 됩니다.
                  시스템이 자동 보정합니다.
                </p>
              </div>
            </div>
          ))}

          {/* Add channel */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="input-terminal text-xs"
              value={addPreset}
              disabled={busy}
              onChange={(e) => setAddPreset(e.target.value)}
            >
              {Object.entries(CHANNEL_PRESETS).map(([key, preset]) => (
                <option key={key} value={key}>
                  {preset.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-secondary !px-3 !py-1.5 text-xs"
              disabled={busy}
              onClick={addChannel}
            >
              + 채널 추가
            </button>
          </div>

          {/* Save */}
          {hasChanges && (
            <div className="flex items-center gap-3 border-t border-white/8 pt-3">
              <button
                type="button"
                className="btn-primary !px-4 !py-1.5 text-xs"
                disabled={busy}
                onClick={() => void handleSave()}
              >
                {isSaving ? '저장 중...' : '채널 저장'}
              </button>
              <button
                type="button"
                className="btn-secondary !px-3 !py-1.5 text-xs"
                disabled={busy}
                onClick={() => setChannels(initialChannels)}
              >
                되돌리기
              </button>
              <span className="text-[11px] text-muted">
                채널 설정은 별도로 저장되며 아래 필드와 서로 영향을 주지 않습니다.
              </span>
            </div>
          )}

          {saveMessage && (
            saveMessage.type === 'success'
              ? <p className="text-xs text-green-400">{saveMessage.text}</p>
              : <ApiErrorAlert error={saveMessage.error} />
          )}
        </div>
      )}
    </div>
  );
};

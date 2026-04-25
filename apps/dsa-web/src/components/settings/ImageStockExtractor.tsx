import type React from 'react';
import { useCallback, useState } from 'react';
import type { ParsedApiError } from '../../api/error';
import { createParsedApiError, getParsedApiError } from '../../api/error';
import { ApiErrorAlert } from '../common';
import { stocksApi } from '../../api/stocks';
import { systemConfigApi, SystemConfigConflictError } from '../../api/systemConfig';

const ALLOWED_EXT = ['.jpg', '.jpeg', '.png', '.webp', '.gif'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB

interface ImageStockExtractorProps {
  stockListValue: string;
  configVersion: string;
  maskToken: string;
  onMerged: () => void;
  disabled?: boolean;
}

export const ImageStockExtractor: React.FC<ImageStockExtractorProps> = ({
  stockListValue,
  configVersion,
  maskToken,
  onMerged,
  disabled,
}) => {
  const [codes, setCodes] = useState<string[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const parseCurrentList = useCallback(() => {
    return stockListValue
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean);
  }, [stockListValue]);

  const handleFile = useCallback(
    async (file: File) => {
      const ext = '.' + (file.name.split('.').pop() ?? '').toLowerCase();
      if (!ALLOWED_EXT.includes(ext)) {
        setError(createParsedApiError({
          title: '지원하지 않는 파일 형식',
          message: 'JPG, PNG, WebP, GIF 형식만 지원합니다.',
          category: 'unknown',
        }));
        return;
      }
      if (file.size > MAX_SIZE) {
        setError(createParsedApiError({
          title: '이미지 크기 제한 초과',
          message: '이미지 크기는 5MB를 초과할 수 없습니다.',
          category: 'unknown',
        }));
        return;
      }

      setError(null);
      setIsExtracting(true);
      try {
        const res = await stocksApi.extractFromImage(file);
        setCodes(res.codes ?? []);
      } catch (e) {
        setError(getParsedApiError(e));
        setCodes([]);
      } finally {
        setIsExtracting(false);
      }
    },
    [],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const f = e.dataTransfer?.files?.[0];
      if (f) void handleFile(f);
    },
    [handleFile],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) void handleFile(f);
      e.target.value = '';
    },
    [handleFile],
  );

  const removeCode = useCallback((code: string) => {
    setCodes((prev) => prev.filter((c) => c !== code));
  }, []);

  const mergeToWatchlist = useCallback(async () => {
    if (codes.length === 0) return;
    if (!configVersion) {
      setError(createParsedApiError({
        title: '설정이 아직 로드되지 않음',
        message: '설정을 먼저 불러온 뒤 병합하세요.',
        category: 'unknown',
      }));
      return;
    }
    const current = parseCurrentList();
    const merged = [...new Set([...current, ...codes])];
    const value = merged.join(',');

    setIsMerging(true);
    setError(null);
    try {
      await systemConfigApi.update({
        configVersion,
        maskToken,
        reloadNow: true,
        items: [{ key: 'STOCK_LIST', value }],
      });
      setCodes([]);
      onMerged();
    } catch (e) {
      if (e instanceof SystemConfigConflictError) {
        onMerged();
        setError(createParsedApiError({
          title: '설정이 변경됨',
          message: '설정이 업데이트되었습니다. “관심 종목에 병합”을 다시 클릭하세요.',
          rawMessage: e.parsedError.rawMessage,
          status: e.parsedError.status,
          category: e.parsedError.category,
        }));
      } else {
        setError(getParsedApiError(e));
      }
    } finally {
      setIsMerging(false);
    }
  }, [codes, configVersion, maskToken, onMerged, parseCurrentList]);

  return (
    <div className="rounded-xl border border-white/8 bg-elevated/40 p-4">
      <p className="mb-2 text-sm font-medium text-white">이미지에서 추가</p>
      <p className="mb-3 text-xs text-muted">
        관심 종목 스크린샷을 업로드하면 종목 코드를 자동 인식합니다.
        Gemini, Anthropic 또는 OpenAI API Key가 필요하며, 병합 전 직접 확인하는 것을 권장합니다.
      </p>

      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={`mb-3 flex min-h-[100px] cursor-pointer flex-col items-center justify-center rounded-lg
          border-2 border-dashed transition ${
          isDragging ? 'border-accent bg-cyan/5' : 'border-white/16 hover:border-white/24'
        } ${disabled || isExtracting ? 'cursor-not-allowed opacity-60' : ''}`}
        onClick={() => !disabled && !isExtracting && document.getElementById('img-upload')?.click()}
      >
        <input
          id="img-upload"
          type="file"
          accept=".jpg,.jpeg,.png,.webp,.gif"
          className="hidden"
          onChange={onFileInput}
          disabled={disabled || isExtracting}
        />
        {isExtracting ? (
          <span className="text-sm text-secondary">인식 중...</span>
        ) : (
          <span className="text-sm text-secondary">
            이미지를 끌어오거나 클릭해 업로드하세요(JPG/PNG/WebP, 5MB 이하).
            큰 이미지는 약 30-60초가 걸립니다.
          </span>
        )}
      </div>

      {error ? (
        <ApiErrorAlert error={error} className="mb-3" />
      ) : null}

      {codes.length > 0 ? (
        <div className="space-y-2">
          <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-xs text-amber-400">
            ⚠️ 인식 결과가 틀릴 수 있으니 병합 전 항목별로 직접 확인하세요
          </p>
          <p className="text-xs text-secondary">인식 결과(필요 없는 항목은 삭제 가능):</p>
          <div className="flex flex-wrap gap-2">
            {codes.map((code) => (
              <span
                key={code}
                className="inline-flex items-center gap-1 rounded-lg border border-white/16
                  bg-card/60 px-2 py-1 text-sm"
              >
                {code}
                <button
                  type="button"
                  className="text-muted hover:text-white"
                  onClick={() => removeCode(code)}
                  disabled={disabled}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          <button
            type="button"
            className="btn-primary mt-2"
            onClick={() => void mergeToWatchlist()}
            disabled={disabled || isMerging}
          >
            {isMerging ? '저장 중...' : '관심 종목에 병합'}
          </button>
        </div>
      ) : null}
    </div>
  );
};

interface ValidationResult {
  valid: boolean;
  message?: string;
  normalized: string;
}

// 한국 / 중국 / 홍콩 / 미국 주식 코드 형식 검증
export const validateStockCode = (value: string): ValidationResult => {
  const normalized = value.trim().toUpperCase();

  if (!normalized) {
    return { valid: false, message: '주식 코드를 입력해주세요', normalized };
  }

  const patterns = [
    /^\d{6}$/, // 한국 주식 6자리 숫자
    /^(SH|SZ)\d{6}$/, // 중국 A주 거래소 접두사 포함
    /^\d{5}$/, // 홍콩 주식 5자리 숫자
    /^[A-Z]{1,6}(\.[A-Z]{1,2})?$/, // 미국 주식 Ticker
    /^(KOSPI|KOSDAQ|KS200)$/i, // 한국 지수
    /^(SPX|DJI|IXIC|NDX|VIX|RUT)$/i, // 미국 지수
  ];

  const valid = patterns.some((regex) => regex.test(normalized));

  return {
    valid,
    message: valid ? undefined : '주식 코드 형식이 올바르지 않습니다',
    normalized,
  };
};

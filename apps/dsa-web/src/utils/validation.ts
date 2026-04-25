interface ValidationResult {
  valid: boolean;
  message?: string;
  normalized: string;
}

// Validate supported KR/US stock and index code formats.
export const validateStockCode = (value: string): ValidationResult => {
  const normalized = value.trim().toUpperCase();

  if (!normalized) {
    return { valid: false, message: '주식 코드를 입력해주세요', normalized };
  }

  const patterns = [
    /^\d{6}$/, // Korean stock codes
    /^(KOSPI|KS11|\^KS11|KOSDAQ|KQ11|\^KQ11|KS200|KOSPI200|\^KS200|KRX300)$/, // Korean indices
    /^(SPX|\^GSPC|GSPC|DJI|\^DJI|DJIA|IXIC|\^IXIC|NASDAQ|NDX|\^NDX|VIX|\^VIX|RUT|\^RUT)$/, // US indices
    /^[A-Z]{1,5}(\.[A-Z])?$/, // US stock tickers
  ];

  const valid = patterns.some((regex) => regex.test(normalized));

  return {
    valid,
    message: valid ? undefined : '주식 코드 형식이 올바르지 않습니다',
    normalized,
  };
};

import type React from 'react';
import { useState } from 'react';
import { ApiErrorAlert } from '../components/common';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { ParsedApiError } from '../api/error';
import { isParsedApiError } from '../api/error';
import { useAuth } from '../hooks';
import { SettingsAlert } from '../components/settings';

const LoginPage: React.FC = () => {
  const { login, passwordSet } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const rawRedirect = searchParams.get('redirect') ?? '';
  const redirect =
    rawRedirect.startsWith('/') && !rawRedirect.startsWith('//') ? rawRedirect : '/';

  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | ParsedApiError | null>(null);

  const isFirstTime = !passwordSet;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (isFirstTime && password !== passwordConfirm) {
      setError('비밀번호와 확인 값이 일치하지 않습니다.');
      return;
    }
    setIsSubmitting(true);
    try {
      const result = await login(password, isFirstTime ? passwordConfirm : undefined);
      if (result.success) {
        navigate(redirect, { replace: true });
      } else {
        setError(result.error ?? '로그인 실패');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-base px-4">
      <div className="w-full max-w-sm rounded-2xl border border-white/8 bg-card/80 p-6 backdrop-blur-sm">
        <h1 className="mb-2 text-xl font-semibold text-white">
          {isFirstTime ? '초기 비밀번호 설정' : '관리자 로그인'}
        </h1>
        <p className="mb-6 text-sm text-secondary">
          {isFirstTime
            ? '관리자 비밀번호를 설정하고 한 번 더 입력해 확인하세요'
            : '계속하려면 비밀번호를 입력하세요'}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-secondary">
              {isFirstTime ? '새 비밀번호' : '비밀번호'}
            </label>
            <input
              id="password"
              type="password"
              className="input-terminal"
              placeholder={isFirstTime ? '새 비밀번호 입력' : '비밀번호 입력'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSubmitting}
              autoFocus
              autoComplete={isFirstTime ? 'new-password' : 'current-password'}
            />
          </div>

          {isFirstTime ? (
            <div>
              <label
                htmlFor="passwordConfirm"
                className="mb-1 block text-sm font-medium text-secondary"
              >
                비밀번호 확인
              </label>
              <input
                id="passwordConfirm"
                type="password"
                className="input-terminal"
                placeholder="비밀번호 다시 입력"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                disabled={isSubmitting}
                autoComplete="new-password"
              />
            </div>
          ) : null}

          {error
            ? isParsedApiError(error)
              ? <ApiErrorAlert error={error} className="!mt-3" />
              : (
                <SettingsAlert
                  title={isFirstTime ? '설정 실패' : '로그인 실패'}
                  message={error}
                  variant="error"
                  className="!mt-3"
                />
              )
            : null}

          <button
            type="submit"
            className="btn-primary w-full"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? (isFirstTime ? '설정 중...' : '로그인 중...')
              : (isFirstTime ? '비밀번호 설정' : '로그인')}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;

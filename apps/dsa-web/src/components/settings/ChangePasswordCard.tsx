import type React from 'react';
import { useState } from 'react';
import type { ParsedApiError } from '../../api/error';
import { isParsedApiError } from '../../api/error';
import { useAuth } from '../../hooks';
import { ApiErrorAlert, EyeToggleIcon } from '../common';
import { SettingsAlert } from './SettingsAlert';

export const ChangePasswordCard: React.FC = () => {
  const { changePassword } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | ParsedApiError | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!currentPassword.trim()) {
      setError('현재 비밀번호를 입력해 주세요');
      return;
    }
    if (!newPassword.trim()) {
      setError('새 비밀번호를 입력해 주세요');
      return;
    }
    if (newPassword.length < 6) {
      setError('새 비밀번호는 최소 6자 이상이어야 합니다');
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      setError('새 비밀번호가 일치하지 않습니다');
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await changePassword(currentPassword, newPassword, newPasswordConfirm);
      if (result.success) {
        setSuccess(true);
        setCurrentPassword('');
        setNewPassword('');
        setNewPasswordConfirm('');
        setShowCurrent(false);
        setShowNew(false);
        setShowConfirm(false);
        setTimeout(() => setSuccess(false), 4000);
      } else {
        setError(result.error ?? '변경 실패');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-white/8 bg-elevated/50 p-4">
      <div className="mb-2 flex items-center gap-2">
        <label className="text-sm font-semibold text-white">비밀번호 변경</label>
      </div>
      <p className="mb-3 text-xs text-muted">관리자 로그인 비밀번호를 변경합니다</p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label
            htmlFor="change-pass-current"
            className="mb-1 block text-xs font-medium text-secondary"
          >
            현재 비밀번호
          </label>
          <div className="flex items-center gap-2">
            <input
              id="change-pass-current"
              type={showCurrent ? 'text' : 'password'}
              className="input-terminal flex-1"
              placeholder="현재 비밀번호 입력"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              disabled={isSubmitting}
              autoComplete="current-password"
            />
            <button
              type="button"
              className="btn-secondary !p-2 shrink-0"
              disabled={isSubmitting}
              onClick={() => setShowCurrent((v) => !v)}
              title={showCurrent ? '숨기기' : '표시'}
              aria-label={showCurrent ? '비밀번호 숨기기' : '비밀번호 표시'}
            >
              <EyeToggleIcon visible={showCurrent} />
            </button>
          </div>
        </div>
        <div>
          <label
            htmlFor="change-pass-new"
            className="mb-1 block text-xs font-medium text-secondary"
          >
            새 비밀번호
          </label>
          <div className="flex items-center gap-2">
            <input
              id="change-pass-new"
              type={showNew ? 'text' : 'password'}
              className="input-terminal flex-1"
              placeholder="새 비밀번호 입력(최소 6자)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={isSubmitting}
              autoComplete="new-password"
            />
            <button
              type="button"
              className="btn-secondary !p-2 shrink-0"
              disabled={isSubmitting}
              onClick={() => setShowNew((v) => !v)}
              title={showNew ? '숨기기' : '표시'}
              aria-label={showNew ? '비밀번호 숨기기' : '비밀번호 표시'}
            >
              <EyeToggleIcon visible={showNew} />
            </button>
          </div>
        </div>
        <div>
          <label
            htmlFor="change-pass-confirm"
            className="mb-1 block text-xs font-medium text-secondary"
          >
            새 비밀번호 확인
          </label>
          <div className="flex items-center gap-2">
            <input
              id="change-pass-confirm"
              type={showConfirm ? 'text' : 'password'}
              className="input-terminal flex-1"
              placeholder="새 비밀번호 다시 입력"
              value={newPasswordConfirm}
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              disabled={isSubmitting}
              autoComplete="new-password"
            />
            <button
              type="button"
              className="btn-secondary !p-2 shrink-0"
              disabled={isSubmitting}
              onClick={() => setShowConfirm((v) => !v)}
              title={showConfirm ? '숨기기' : '표시'}
              aria-label={showConfirm ? '비밀번호 숨기기' : '비밀번호 표시'}
            >
              <EyeToggleIcon visible={showConfirm} />
            </button>
          </div>
        </div>

        {error
          ? isParsedApiError(error)
            ? <ApiErrorAlert error={error} className="!mt-3" />
            : <SettingsAlert title="변경 실패" message={error} variant="error" className="!mt-3" />
          : null}
        {success ? (
          <p className="text-xs text-green-500">비밀번호가 변경되었습니다</p>
        ) : null}

        <button
          type="submit"
          className="btn-primary mt-2"
          disabled={isSubmitting}
        >
          {isSubmitting ? '변경 중...' : '변경'}
        </button>
      </form>
    </div>
  );
};

import { useMutation } from '@tanstack/react-query';
import { authAPI } from '@/lib/api/auth';
import { PasswordResetRequest, PasswordResetConfirm } from '@/types';

export function usePasswordReset() {
  // Request password reset
  const requestResetMutation = useMutation({
    mutationFn: (data: PasswordResetRequest) => authAPI.requestPasswordReset(data),
  });

  // Confirm password reset
  const confirmResetMutation = useMutation({
    mutationFn: (data: PasswordResetConfirm) => authAPI.confirmPasswordReset(data),
  });

  return {
    requestReset: requestResetMutation.mutate,
    isRequesting: requestResetMutation.isPending,
    requestError: requestResetMutation.error,
    requestSuccess: requestResetMutation.isSuccess,
    confirmReset: confirmResetMutation.mutate,
    isConfirming: confirmResetMutation.isPending,
    confirmError: confirmResetMutation.error,
    confirmSuccess: confirmResetMutation.isSuccess,
  };
}

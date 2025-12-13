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
    // Use mutateAsync for async/await support in components
    requestReset: requestResetMutation.mutateAsync,
    isRequesting: requestResetMutation.isPending,
    requestError: requestResetMutation.error,
    requestSuccess: requestResetMutation.isSuccess,
    confirmReset: confirmResetMutation.mutateAsync,
    isConfirming: confirmResetMutation.isPending,
    confirmError: confirmResetMutation.error,
    confirmSuccess: confirmResetMutation.isSuccess,
  };
}

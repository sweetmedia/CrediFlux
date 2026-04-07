import { useMutation } from '@tanstack/react-query';
import { authAPI } from '@/lib/api/auth';
import { EmailVerificationRequest, EmailVerificationConfirm } from '@/types';

export function useEmailVerification() {
  // Send verification email
  const sendVerificationMutation = useMutation({
    mutationFn: (data: EmailVerificationRequest) => authAPI.sendEmailVerification(data),
  });

  // Confirm email verification
  const confirmVerificationMutation = useMutation({
    mutationFn: (data: EmailVerificationConfirm) => authAPI.confirmEmailVerification(data),
  });

  return {
    sendVerification: sendVerificationMutation.mutate,
    isSending: sendVerificationMutation.isPending,
    sendError: sendVerificationMutation.error,
    sendSuccess: sendVerificationMutation.isSuccess,
    confirmVerification: confirmVerificationMutation.mutate,
    isConfirming: confirmVerificationMutation.isPending,
    confirmError: confirmVerificationMutation.error,
    confirmSuccess: confirmVerificationMutation.isSuccess,
  };
}

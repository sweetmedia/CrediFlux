import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authAPI } from '@/lib/api/auth';
import { ProfileUpdateData, PasswordChangeData } from '@/types';
import { useAuth } from '@/lib/contexts/AuthContext';

export function useProfile() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();

  // Get profile
  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['profile'],
    queryFn: authAPI.getProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Update profile
  const updateProfileMutation = useMutation({
    mutationFn: (data: ProfileUpdateData) => authAPI.updateProfile(data),
    onSuccess: async (data) => {
      // Update cache
      queryClient.setQueryData(['profile'], data);

      // Refresh auth context
      await refreshUser();
    },
  });

  // Change password
  const changePasswordMutation = useMutation({
    mutationFn: (data: PasswordChangeData) => authAPI.changePassword(data),
  });

  return {
    profile,
    isLoading,
    error,
    updateProfile: updateProfileMutation.mutate,
    isUpdatingProfile: updateProfileMutation.isPending,
    updateProfileError: updateProfileMutation.error,
    changePassword: changePasswordMutation.mutate,
    isChangingPassword: changePasswordMutation.isPending,
    changePasswordError: changePasswordMutation.error,
  };
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authAPI } from '@/lib/api/auth';
import { TeamMemberCreate, TeamMemberUpdate } from '@/types';

export function useTeam() {
  const queryClient = useQueryClient();

  // Get team members
  const { data: teamMembers, isLoading, error } = useQuery({
    queryKey: ['team'],
    queryFn: authAPI.getTeamMembers,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Get single team member
  const getTeamMember = (id: number) => {
    return useQuery({
      queryKey: ['team', id],
      queryFn: () => authAPI.getTeamMember(id),
      enabled: !!id,
    });
  };

  // Create team member
  const createTeamMemberMutation = useMutation({
    mutationFn: (data: TeamMemberCreate) => authAPI.createTeamMember(data),
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['team'] });
    },
  });

  // Update team member
  const updateTeamMemberMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: TeamMemberUpdate }) =>
      authAPI.updateTeamMember(id, data),
    onSuccess: (_data, variables) => {
      // Invalidate specific member and list
      queryClient.invalidateQueries({ queryKey: ['team', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['team'] });
    },
  });

  // Delete team member
  const deleteTeamMemberMutation = useMutation({
    mutationFn: (id: number) => authAPI.deleteTeamMember(id),
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['team'] });
    },
  });

  return {
    teamMembers,
    isLoading,
    error,
    getTeamMember,
    createTeamMember: createTeamMemberMutation.mutate,
    isCreating: createTeamMemberMutation.isPending,
    createError: createTeamMemberMutation.error,
    updateTeamMember: updateTeamMemberMutation.mutate,
    isUpdating: updateTeamMemberMutation.isPending,
    updateError: updateTeamMemberMutation.error,
    deleteTeamMember: deleteTeamMemberMutation.mutate,
    isDeleting: deleteTeamMemberMutation.isPending,
    deleteError: deleteTeamMemberMutation.error,
  };
}

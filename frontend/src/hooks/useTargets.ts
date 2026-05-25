import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API_URL = '/api/v1';

export function useTargets() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['targets'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/targets`);
      return response.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (newTarget: { name: string; base_url: string; authorized?: boolean }) => {
      const response = await axios.post(`${API_URL}/targets`, newTarget);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (targetId: number) => {
      await axios.delete(`${API_URL}/targets/${targetId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
    },
  });

  return {
    targets: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    createTarget: createMutation.mutateAsync,
    deleteTarget: deleteMutation.mutateAsync,
  };
}

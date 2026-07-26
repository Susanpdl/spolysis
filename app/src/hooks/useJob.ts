import { useQuery } from '@tanstack/react-query';
import { api, Job, Result } from '@/services/api';

export function useJob(jobId: string | null) {
  const jobQuery = useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: () => api.jobs.get(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'pending' || status === 'processing') return 2000;
      return false;
    },
    staleTime: 1000,
  });

  const resultQuery = useQuery<Result>({
    queryKey: ['job-result', jobId],
    queryFn: () => api.jobs.getResult(jobId!),
    enabled: !!jobId && jobQuery.data?.status === 'completed',
  });

  return {
    job: jobQuery.data,
    result: resultQuery.data,
    isLoadingJob: jobQuery.isLoading,
    isLoadingResult: resultQuery.isLoading,
    jobError: jobQuery.error,
    resultError: resultQuery.error,
  };
}

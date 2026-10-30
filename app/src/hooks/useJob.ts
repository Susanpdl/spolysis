import { useQuery } from "@tanstack/react-query";
import { authStore } from "@/store/authStore";
import { api, Job, Result } from "@/services/api";

export function useJob(jobId: string | null) {
  const userId = authStore((s) => s.user?.id);
  const jobQuery = useQuery<Job>({
    queryKey: ["job", userId, jobId],
    queryFn: () => api.jobs.get(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === "pending" || status === "processing")
        return 2000;
      return false;
    },
    staleTime: 1000,
  });

  const resultQuery = useQuery<Result>({
    queryKey: ["job-result", userId, jobId],
    queryFn: () => api.jobs.getResult(jobId!),
    enabled: !!jobId && jobQuery.data?.status === "completed",
  });

  return {
    job: jobQuery.data,
    result: resultQuery.data,
    isLoadingJob: jobQuery.isLoading,
    isLoadingResult: resultQuery.isLoading,
    isFetchingResult: resultQuery.isFetching,
    jobError: jobQuery.error,
    resultError: resultQuery.error,
    refetchResult: resultQuery.refetch,
    refetch: async () => {
      const job = await jobQuery.refetch();
      if (job.data?.status === "completed") await resultQuery.refetch();
    },
  };
}

import { create } from 'zustand';

interface RecordingState {
  videoUri: string | null;
  jobId: string | null;
  isUploading: boolean;
  uploadProgress: number;
  setVideoUri: (uri: string) => void;
  setJobId: (id: string) => void;
  setUploadProgress: (progress: number) => void;
  setUploading: (uploading: boolean) => void;
  reset: () => void;
}

export const recordingStore = create<RecordingState>((set) => ({
  videoUri: null,
  jobId: null,
  isUploading: false,
  uploadProgress: 0,
  setVideoUri: (videoUri) => set({ videoUri }),
  setJobId: (jobId) => set({ jobId }),
  setUploadProgress: (uploadProgress) => set({ uploadProgress }),
  setUploading: (isUploading) => set({ isUploading }),
  reset: () => set({ videoUri: null, jobId: null, isUploading: false, uploadProgress: 0 }),
}));

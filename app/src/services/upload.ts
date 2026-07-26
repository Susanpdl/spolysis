import { api } from './api';

function putToR2(
  uri: string,
  url: string,
  onProgress?: (progress: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', 'video/mp4');

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(e.loaded / e.total);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error('Upload network error'));

    fetch(uri)
      .then((r) => r.blob())
      .then((blob) => xhr.send(blob))
      .catch(reject);
  });
}

export const uploadService = {
  upload: (uri: string, url: string, onProgress?: (progress: number) => void) =>
    putToR2(uri, url, onProgress),
};

export async function uploadVideoToR2(
  videoUri: string,
  tier: 'free' | 'premium',
  onProgress?: (progress: number) => void,
): Promise<{ job_id: string }> {
  const filename = `recording_${Date.now()}.mp4`;
  const { upload_url, job_id } = await api.uploads.getUrl(tier, filename);
  await putToR2(videoUri, upload_url, onProgress);
  return { job_id };
}

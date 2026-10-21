import { File, UploadTask, UploadType } from "expo-file-system";

export function createVideoUpload(
  uri: string,
  url: string,
  contentType: string,
  onProgress: (progress: number) => void,
) {
  const normalized = uri.startsWith("/") ? `file://${uri}` : uri;
  return new UploadTask(new File(normalized), url, {
    httpMethod: "PUT",
    uploadType: UploadType.BINARY_CONTENT,
    headers: { "Content-Type": contentType },
    sessionType: "foreground",
    onProgress: ({ bytesSent, totalBytes }) =>
      onProgress(totalBytes > 0 ? bytesSent / totalBytes : 0),
  });
}

export type ImportedVideoStatus = "imported" | "ready";

export interface ImportedVideo {
  id: string;
  projectId: string;
  filePath: string;
  fileName: string;
  fileSizeBytes: number;
  durationSeconds: number | null;
  width: number | null;
  height: number | null;
  frameRate: number | null;
  codec: string | null;
  status: ImportedVideoStatus;
  errorMessage: string | null;
  createdAt: string;
}

"use client";
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { BatchJobStatus } from "@/types";
import { Sidebar } from "@/components/shared/Sidebar";
import toast from "react-hot-toast";
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { clsx } from "clsx";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { "text/csv": [".csv"] }, maxFiles: 1,
  });

  const uploadMutation = useMutation({
    mutationFn: async (f: File) => {
      const form = new FormData();
      form.append("file", f);
      const { data } = await api.post("/predict/batch", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data as BatchJobStatus;
    },
    onSuccess: (data) => {
      setJobId(data.job_id);
      toast.success("Batch job queued!");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "Upload failed"),
  });

  const { data: jobStatus } = useQuery<BatchJobStatus>({
    queryKey: ["batch-job", jobId],
    queryFn: () => api.get(`/predict/batch/${jobId}`).then((r) => r.data),
    enabled: !!jobId,
    refetchInterval: (data) =>
      data?.status === "completed" || data?.status === "failed" ? false : 2000,
  });

  const status = jobStatus?.status;
  const progress = jobStatus?.total
    ? Math.round(((jobStatus.processed ?? 0) / jobStatus.total) * 100)
    : 0;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-6">
          <h1 className="text-headline-md font-headline font-bold text-on-surface">Batch CSV Upload</h1>
          <p className="text-body-md text-on-surface-variant mt-1">Upload a CSV with columns: Time, Amount, V1-V28 (optionally Class)</p>
        </div>

        <div className="max-w-2xl space-y-6">
          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={clsx(
              "card p-10 border-2 border-dashed cursor-pointer text-center transition-colors",
              isDragActive ? "border-secondary bg-secondary-container/20" : "border-outline-variant hover:border-secondary/50"
            )}
          >
            <input {...getInputProps()} />
            <Upload className="w-10 h-10 text-on-surface-dim mx-auto mb-3" />
            {file ? (
              <div>
                <div className="flex items-center justify-center gap-2 text-secondary">
                  <FileText className="w-5 h-5" />
                  <span className="font-medium">{file.name}</span>
                </div>
                <p className="text-sm text-on-surface-dim mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <>
                <p className="font-medium text-on-surface">Drop your CSV here, or click to browse</p>
                <p className="text-sm text-on-surface-dim mt-1">Max 100 MB - CSV only</p>
              </>
            )}
          </div>

          <button
            onClick={() => file && uploadMutation.mutate(file)}
            disabled={!file || uploadMutation.isPending || status === "pending" || status === "started"}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {uploadMutation.isPending
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</>
              : <><Upload className="w-4 h-4" /> Start Batch Prediction</>}
          </button>

          {/* Job status */}
          {jobStatus && (
            <div className="card p-5">
              <div className="flex items-center gap-3 mb-4">
                {status === "completed" && <CheckCircle className="w-5 h-5 text-success" />}
                {status === "failed"    && <XCircle className="w-5 h-5 text-error" />}
                {(status === "pending" || status === "started") && (
                  <Loader2 className="w-5 h-5 text-secondary animate-spin" />
                )}
                <span className="font-semibold capitalize text-on-surface">{status}</span>
              </div>

              {(status === "started" || status === "completed") && (
                <div className="mb-4">
                  <div className="flex justify-between text-sm text-on-surface-variant mb-1">
                    <span>Progress</span>
                    <span>{jobStatus.processed ?? 0} / {jobStatus.total ?? "?"}</span>
                  </div>
                  <div className="metric-bar-track">
                    <div
                      className="metric-bar-fill bg-secondary"
                      style={{ width: `${status === "completed" ? 100 : progress}%` }}
                    />
                  </div>
                </div>
              )}

              {status === "completed" && (
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="bg-surface-container rounded-lg p-3">
                    <p className="text-2xl font-bold text-on-surface">{jobStatus.total?.toLocaleString()}</p>
                    <p className="text-xs text-on-surface-dim mt-0.5">Total</p>
                  </div>
                  <div className="bg-surface-error rounded-lg p-3">
                    <p className="text-2xl font-bold text-error">{jobStatus.fraud_count?.toLocaleString()}</p>
                    <p className="text-xs text-on-surface-dim mt-0.5">Fraud</p>
                  </div>
                  <div className="bg-surface-success rounded-lg p-3">
                    <p className="text-2xl font-bold text-success">
                      {((jobStatus.total ?? 0) - (jobStatus.fraud_count ?? 0)).toLocaleString()}
                    </p>
                    <p className="text-xs text-on-surface-dim mt-0.5">Legitimate</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

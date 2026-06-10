import { ElMessage } from "element-plus";
import { createExportJob } from "@/api/exportJob";

export async function submitExportJob(data: {
    export_type: string;
    title: string;
    filename: string;
    params: Record<string, any>;
}) {
    const job = await createExportJob(data);
    ElMessage.success(`导出任务「${job.title || data.title}」已加入下载中心`);
    return job;
}

export function normalizeExportFilename(filename: string) {
    const cleaned = filename.replace(/[\\/:*?"<>|\r\n]+/g, "_").trim();
    return cleaned.toLowerCase().endsWith(".xlsx") ? cleaned : `${cleaned || "导出文件"}.xlsx`;
}

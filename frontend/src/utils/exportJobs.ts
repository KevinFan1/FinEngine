import { ElMessage, ElMessageBox } from "element-plus";
import router from "@/router";
import { createExportJob } from "@/api/exportJob";
import { navigateToDownloadCenter } from "./downloadCenterNavigation";

export async function submitExportJob(data: {
    export_type: string;
    title: string;
    filename: string;
    params: Record<string, any>;
}) {
    const job = await createExportJob(data);
    const goDownloadCenter = await ElMessageBox.confirm(
            `导出任务「${job.title || data.title}」已加入下载中心，生成完成后可下载。`,
            "已提交导出",
            {
                type: "success",
                confirmButtonText: "去下载中心",
                cancelButtonText: "继续停留",
                customClass: "export-job-message-box",
                distinguishCancelAndClose: true,
            },
        )
        .then(() => true)
        .catch(() => false);

    if (goDownloadCenter) {
        await openDownloadCenter();
    } else {
        ElMessage.success("已加入下载中心");
    }
    return job;
}

export async function openDownloadCenter() {
    await navigateToDownloadCenter(router, window.location);
}

export function normalizeExportFilename(filename: string) {
    const cleaned = filename.replace(/[\\/:*?"<>|\r\n]+/g, "_").trim();
    return cleaned.toLowerCase().endsWith(".xlsx") ? cleaned : `${cleaned || "导出文件"}.xlsx`;
}

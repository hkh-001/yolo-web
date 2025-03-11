import { ElMessage, type MessageFn } from "element-plus";

export const Message: Pick<typeof ElMessage, "closeAll" | "info" | "success" | "warning" | "error"> & { of: MessageFn; } = { ...ElMessage, of: ElMessage };
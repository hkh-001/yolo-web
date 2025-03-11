import { ElMessage, type MessageFn } from "element-plus";

export const Message: Pick<typeof ElMessage, "closeAll" | "info" | "success" | "warning" | "error"> & { of: MessageFn; } = {
    ...ElMessage, of: ElMessage, error: (...args) => {
        if (typeof args[0] === 'string') args[0] = { message: args[0], duration: 5000 };
        return ElMessage.error(...args);
    }
};
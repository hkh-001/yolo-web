// 应用全局导航配置

export const HEADER_NAV = [
    { href: "/", text: "主页" },
    { href: "/predict", text: "识别" },
    { href: "/train", text: "训练" },
    { href: "/history", text: "历史记录" }
] as const;

// 侧边栏导航
export const ASIDE_NAV = [
    { href: "/", text: "主页" },
    { href: "/predict/image", text: "图像识别" },
    { href: "/predict/video", text: "视频识别" },
    { href: "/predict/mask", text: "掩码生成" },
    { href: "/predict/enhance", text: "图像增强" },
    { href: "/predict/workflow", text: "智能流程" },
    { href: "/train", text: "模型训练" },
    { href: "/history", text: "历史记录" }
] as const;

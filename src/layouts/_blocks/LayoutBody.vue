<script lang="ts" setup>
import { ElContainer, ElHeader, ElAside, ElMain } from "element-plus";
</script>

<template>
    <div class="common-layout h-screen">
        <ElContainer class="h-full">
            <!-- 顶部导航栏：深色科技风，毛玻璃效果 -->
            <ElHeader class="sticky z-1000 top-0 left-0 !p-0 !h-auto tech-header">
                <slot name="header" />
            </ElHeader>
            <ElContainer class="relative z-0 h-full">
                <ElAside width="200px"></ElAside>
                <ElAside width="200px" class="fixed h-full">
                    <slot name="aside" />
                </ElAside>
                <ElMain class="!px-8 !py-6 h-max">
                    <slot name="main" />
                </ElMain>
            </ElContainer>
        </ElContainer>
    </div>
</template>

<style scoped>
.common-layout {
    @apply min-h-screen;
}

/* 科技风顶部导航栏 - 毛玻璃效果 */
:global(.tech-header) {
    background: linear-gradient(180deg, 
        rgba(25, 28, 38, 0.95) 0%, 
        rgba(20, 23, 32, 0.92) 100%
    ) !important;
    backdrop-filter: blur(12px) saturate(180%);
    -webkit-backdrop-filter: blur(12px) saturate(180%);
    border-bottom: 1px solid rgba(64, 158, 255, 0.08);
    box-shadow: 
        0 4px 20px rgba(0, 0, 0, 0.15),
        0 1px 0 rgba(64, 158, 255, 0.05) inset;
}

/* 顶部微光效果 */
:global(.tech-header::before) {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, 
        transparent 0%, 
        rgba(64, 158, 255, 0.15) 20%, 
        rgba(0, 200, 200, 0.1) 50%, 
        rgba(64, 158, 255, 0.15) 80%, 
        transparent 100%
    );
    pointer-events: none;
}
</style>

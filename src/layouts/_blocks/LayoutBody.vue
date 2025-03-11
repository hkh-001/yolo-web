<script lang="ts" setup>
import { ElContainer, ElHeader, ElAside, ElMain } from "element-plus";
</script>

<template>
    <div class="common-layout h-screen">
        <ElContainer class="h-full">
            <ElHeader class="sticky z-1000 top-0 left-0 bg-(--bg-color) !p-0 !h-auto">
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
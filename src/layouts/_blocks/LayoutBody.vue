<script lang="ts" setup>
import { ElContainer, ElHeader, ElAside, ElMain } from "element-plus";
</script>

<template>
    <div class="common-layout h-full">
        <el-container class="h-full">
            <el-header class="relative !p-0 !h-auto">
                <slot name="header" />
            </el-header>
            <el-container class="h-full">
                <el-aside width="200px" class="h-full">
                    <slot name="aside" />
                </el-aside>
                <el-main class="!px-8 !py-6">
                    <slot name="main" />
                </el-main>
            </el-container>
        </el-container>
    </div>
</template>
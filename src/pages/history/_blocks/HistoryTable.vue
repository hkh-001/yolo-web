<script setup lang="ts">
import * as api from '@/utils/api';
import type { TaskList } from '@/utils/api/task';
import { Message } from '@/utils/message';
import { ElButton, ElTable, ElTableColumn } from 'element-plus';
import { onMounted, ref } from 'vue';

const taskList = ref<TaskList & { source_name: string }[]>([]);

const categoryMap = {
    "image": "图像识别",
    "video": "视频识别",
    "mask": "掩码生成",
} as const;

async function updateTaskList() {
    api.listTasks().then(tasks => {
        taskList.value = tasks
            .map((task) => ({
                ...task,
                source_name: categoryMap[task.source],
            })).sort((a, b) => a.timestamp - b.timestamp);
    }).catch(e => {
        Message.error('获取任务列表失败');
        console.error(e)
    });
}

onMounted(updateTaskList);

const deletingTask = ref<boolean>(false);
const deleteTask = async (taskId: string) => {
    deletingTask.value = true;
    await api.deleteTask(taskId).then(() => {
        Message.success('删除成功');
        updateTaskList();
    }).catch(e => {
        Message.error('删除失败');
        console.error(e)
    });
    deletingTask.value = false;
};

const fmtTime = (timestamp: number) => {
    const year = new Date(timestamp).getFullYear();
    const month = (new Date(timestamp).getMonth() + 1).toString().padStart(2, '0');
    const day = new Date(timestamp).getDate().toString().padStart(2, '0');
    const hour = new Date(timestamp).getHours().toString().padStart(2, '0');
    const minute = new Date(timestamp).getMinutes().toString().padStart(2, '0');
    const second = new Date(timestamp).getSeconds().toString().padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

const redirectTo = (url: string) => {
    window.location.href = url;
};

</script>

<template>
    <ElTable :data="taskList" class="w-full">
        <ElTableColumn prop="task_name" label="任务名称" />
        <ElTableColumn prop="source_name" label="任务类别" />
        <ElTableColumn prop="timestamp" label="创建时间" :formatter="(_, __, ts) => fmtTime(ts)" />
        <ElTableColumn fixed="right" label="操作" min-width="100">
            <template #default="{ row }">
                <ElButton type="primary" link @click="redirectTo(`/predict/${row.source}?task=${row.task_id}`)">查看
                </ElButton>
                <ElButton type="danger" link target="_self" @click="deleteTask(row.task_id)" :disabled="deletingTask">
                    删除</ElButton>
            </template>
        </ElTableColumn>
    </ElTable>
</template>
import type { PredictData } from "./predict";

export interface Task {
    id: number;
    task_id: string;
    task_name: string;
    timestamp: number;
    source: PredictData["source"];
    input_blob: string;
    input_args: string;
    results: string | null;
    results_blob: string | null;
}

export type TaskList = Pick<Task, "task_id" | "timestamp" | "task_name" | "source">[];
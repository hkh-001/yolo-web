import sqlite3 from 'sqlite3';
import * as uuid from 'uuid';

export interface Task {
    id: number;
    task_id: string;
    task_name: string;
    timestamp: number;
    source: string;
    input_blob: string;
    input_args: string;
    results: string | null;
    results_blob: string | null;
}

export class Sqlite {
    private db: sqlite3.Database;
    private file: string;

    constructor(file: string) {
        this.file = file;
        this.db = new sqlite3.Database(file, (err) => {
            if (err) {
                console.error(err.message);
            } else {
                console.log(`Database connected to ${this.file}`);
                this.init()
            }
        });
    }

    private async init() {
        return new Promise((resolve: (value: boolean) => void, reject: (reason: Error) => void) => {
            this.db.run(`CREATE TABLE IF NOT EXISTS yolo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            timestamp INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            source TEXT NOT NULL,
            input_blob TEXT NOT NULL,
            input_args TEXT NOT NULL,
            results TEXT,
            results_blob TEXT
        )`, (err) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(true);
                }
            })
        })
    }

    public async insertTask(task: Omit<Task, 'id' | 'timestamp'>): Promise<string> {
        return new Promise((resolve: (value: string) => void, reject: (reason: Error) => void) => {
            const task_id = uuid.v4();
            this.db.run(`INSERT INTO yolo (task_id, task_name, timestamp, source, input_blob, input_args, results, results_blob) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`, [
                task_id,
                task.task_name,
                Date.now(),
                task.source,
                task.input_blob,
                task.input_args,
                task.results,
                task.results_blob
            ], (err) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(task_id);
                }
            });
        });
    }

    public async getTask(task_id: string): Promise<Task | null> {
        return new Promise((resolve: (value: Task | null) => void, reject: (reason: Error) => void) => {
            this.db.get(`SELECT * FROM yolo WHERE task_id = ?`, [task_id], (err, row: Task) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(row);
                }
            });
        });
    }

    public async listTasks(): Promise<Pick<Task, "task_id" | "timestamp" | "task_name" | "source">[]> {
        return new Promise((resolve: (value: Task[]) => void, reject: (reason: Error) => void) => {
            this.db.all(`SELECT source, task_id, timestamp, task_name FROM yolo`, (err, rows: Task[]) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(rows);
                }
            });
        });
    }

    public async deleteTask(task_id: string): Promise<void> {
        return new Promise((resolve: () => void, reject: (reason: Error) => void) => {
            this.db.run(`DELETE FROM yolo WHERE task_id = ?`, [task_id], (err) => {
                if (err) {
                    reject(err);
                } else {
                    resolve();
                }
            });
        });
    }

    public existsFile(filename: string): Promise<boolean> {
        return new Promise((resolve: (value: boolean) => void, reject: (reason: Error) => void) => {
            this.db.get(`SELECT EXISTS(SELECT 1 FROM yolo WHERE input_blob = ? or results_blob = ?) as result`, [filename, filename], (err, row: { result: number }) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(!!row.result);
                }
            });
        });
    }
}

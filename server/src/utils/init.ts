import { Sqlite } from "./sql";
import config from "@/config"

await Bun.$`mkdir -p data/files`;

export const sql = new Sqlite(config.database.file);
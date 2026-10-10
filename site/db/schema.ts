// Intentionally empty by default.
// Add Drizzle tables here when the site actually needs a database.
// See examples/d1/db/schema.ts for an opt-in example.
import { sqliteTable, text, integer, index } from "drizzle-orm/sqlite-core";

export const tasks = sqliteTable("relay_tasks", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  operation: text("operation").notNull(),
  arguments: text("arguments").notNull(),
  state: text("state").notNull(),
  result: text("result"),
  created: integer("created").notNull(),
  dispatched: integer("dispatched"),
}, (table) => [index("tasks_state_created").on(table.state, table.created), index("tasks_user_created").on(table.userId, table.created)]);

export const relay = sqliteTable("relay_state", {
  id: text("id").primaryKey(), lastSeen: integer("last_seen").notNull(), allowSwitch: integer("allow_switch").notNull(),
  allowOfficialUpdate: integer("allow_official_update").notNull().default(0),
});

export const officialApprovals = sqliteTable("official_update_approvals", {
  id: text("id").primaryKey(), userId: text("user_id").notNull(),
  digest: text("digest").notNull(), expires: integer("expires").notNull(),
  used: integer("used").notNull().default(0),
});

export const approvals = sqliteTable("switch_approvals", {
  id: text("id").primaryKey(), userId: text("user_id").notNull(), catalogId: text("catalog_id").notNull(),
  digest: text("digest").notNull(), entryMethod: text("entry_method").notNull(), expires: integer("expires").notNull(), used: integer("used").notNull().default(0),
});

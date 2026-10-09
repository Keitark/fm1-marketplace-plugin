CREATE TABLE `switch_approvals` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`catalog_id` text NOT NULL,
	`digest` text NOT NULL,
	`entry_method` text NOT NULL,
	`expires` integer NOT NULL,
	`used` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE TABLE `relay_state` (
	`id` text PRIMARY KEY NOT NULL,
	`last_seen` integer NOT NULL,
	`allow_switch` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `relay_tasks` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`operation` text NOT NULL,
	`arguments` text NOT NULL,
	`state` text NOT NULL,
	`result` text,
	`created` integer NOT NULL,
	`dispatched` integer
);
--> statement-breakpoint
CREATE INDEX `tasks_state_created` ON `relay_tasks` (`state`,`created`);--> statement-breakpoint
CREATE INDEX `tasks_user_created` ON `relay_tasks` (`user_id`,`created`);
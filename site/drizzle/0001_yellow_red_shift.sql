CREATE TABLE `official_update_approvals` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`digest` text NOT NULL,
	`expires` integer NOT NULL,
	`used` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
ALTER TABLE `relay_state` ADD `allow_official_update` integer DEFAULT 0 NOT NULL;
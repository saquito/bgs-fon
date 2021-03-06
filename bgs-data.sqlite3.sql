BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS `ticks` (
	`timestamp`	INTEGER
);
CREATE TABLE IF NOT EXISTS `system_status` (
	`date`	INTEGER,
	`system`	INTEGER,
	`controller_faction`	TEXT,
	`security`	TEXT,
	PRIMARY KEY(`date`,`system`)
);
CREATE TABLE IF NOT EXISTS `faction_system_state` (
	`date`	INTEGER,
	`state_name`	TEXT,
	`state_type`	TEXT,
	`faction_name`	TEXT,
	`system_name`	TEXT,
	`trend`	INTEGER,
	PRIMARY KEY(`date`,`state_name`,`state_type`,`faction_name`,`system_name`)
);
CREATE TABLE IF NOT EXISTS `faction_system` (
	`date`	INTEGER,
	`name`	TEXT,
	`system`	TEXT,
	`influence`	REAL,
	PRIMARY KEY(`date`,`name`,`system`)
);
CREATE TABLE IF NOT EXISTS `Variables` (
	`name`	INTEGER,
	`value`	INTEGER,
	PRIMARY KEY(`name`)
);
CREATE TABLE IF NOT EXISTS `Systems` (
	`name`	TEXT,
	`population`	INTEGER,
	`economy`	TEXT,
	`distance`	REAL,
	`allegiance`	TEXT,
	`faction`	TEXT,
	`factionState`	TEXT,
	PRIMARY KEY(`name`)
);
CREATE TABLE IF NOT EXISTS `Stations` (
	`system`	TEXT,
	`name`	TEXT,
	`type`	TEXT,
	`distance`	REAL,
	`economy`	TEXT,
	`controller`	TEXT,
	PRIMARY KEY(`system`,`name`)
);
CREATE TABLE IF NOT EXISTS `Factions` (
	`faction_name`	TEXT UNIQUE,
	`allegiance`	TEXT,
	`government`	TEXT,
	`is_player`	INTEGER,
	`native_system`	TEXT,
	PRIMARY KEY(`faction_name`)
);
COMMIT;

#!/usr/bin/php
<?php

// Needs to point out the web code... TODO: Avoid this config issue
$sWebPath = "/var/www/html/includes/";

require_once($sWebPath . "/processing.php");

$iErr = 0;

if ($argc < 2) {
	printf("Usage: add_database.php <PDF file>\n");
	$iErr = 255;
} else {
	if (($iErr = InitializeWork()) == 0) {
		if (($iErr = ProcessFile($argv[1], $argc == 3 ? $argv[2] : 0)) != 0) {
			printf("ProcessFile() failed with %d\n", $iErr);
		}
		if (($iErr = CleanupWork()) != 0) {
			printf("CleanupWork() failed with %d\n", $iErr);
		}
	} else
		printf("InitializeWork() failed with %d\n", $iErr);
}

exit($iErr);

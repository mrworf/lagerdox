<?php
	session_start();
	$sKey = ini_get("session.upload_progress.prefix") . "upload";
	
	header("Content-Type: text/plain");

	if (isset($_SESSION[$sKey]) && $_SESSION[$sKey] !== FALSE) {
		$aUpload = $_SESSION[$sKey];
		$iC = 0;
		printf("%d", ($aUpload["bytes_processed"] * 100) / $aUpload["content_length"]);
		foreach ($aUpload["files"] as $aFile) {
			$iC++;
			if ($aFile["done"]) {
				printf("|%d", $iC);
			}
		}
	} else {
		print("inactive\n");
	}

	exit;

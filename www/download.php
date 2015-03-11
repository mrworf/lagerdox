<?php
require_once("includes/db.php");

	$aSafer = array("/" => "-", "\\" => "-", " " => "_", ":" => ".", ";" => ".");

	$objDb = new ScannerDB();
	$objDb->open();

	if (!isset($_GET["id"]))
		die("Invalid parameters");

	$aRes = $objDb->GetDetails($_GET["id"]);

	header("Content-Type: application/pdf");
	header(sprintf('Content-Disposition: attachment; filename="%s_%s_%d_pages.pdf"', strftime("%F", $aRes["added"]), strtr($aRes["name"], $aSafer), $aRes["pages"]));

	readfile($aRes["filename"]);

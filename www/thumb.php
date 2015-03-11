<?php
require_once("includes/db.php");

	header("Content-Type: image/png");

	$objDb = new ScannerDB();
	$objDb->open();

	if (!isset($_GET["id"]) || !isset($_GET["width"]))
		die("Invalid parameters");
		
	if (!isset($_GET["page"]))
		$iPage = 1;
	else
		$iPage = intval($_GET["page"]);
	
	$objDb->ShowThumbnail($_GET["id"], $iPage, $_GET["width"]);

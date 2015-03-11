<?php
require_once("includes/datamining.php");

	$objDM = new DataMining();

	header("Content-Type: application/pdf");
	//header("Content-Type: text/plain");

	$objDM->GenerateSeparator();
	exit;

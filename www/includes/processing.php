<?php
require_once("config.php");
require_once("datamining.php");

/**
 * InitializeWork
 *
 * Creates a unique work directory for this run.
 *
 * @return 0 on success
 *         1 If base temp path isn't a directory
 *         2 If it was unable to create a temp directory
 *         3 base temp directory could not be created
 */
function InitializeWork() {
	// Make sure the temp dir exists
	$sTmpPath = Config::GetPath("tmp");
	if (!file_exists($sTmpPath)) {
		if (mkdir($sTmpPath) === FALSE) {
			return 3;
		}
	}
	
	// Can we use the tmp dir?
	if (!is_dir($sTmpPath)) {
		print("Cannot access " . $sTmpPath);
		return 1;
	}
	
	// We have to make SURE that we can share this directory with
	// the other parts of the system (such as web and/or script)
	chmod($sTmpPath, 0777);	

	// Randomly create a new directory name
	$i = 0;
	$bSuccess = false;
	do {
		$sRandom = "/" . md5(time() . mt_rand() . $i);
		if (!file_exists($sTmpPath . $sRandom)) {
			if (mkdir($sTmpPath . $sRandom) === FALSE) {
				// Hmm, unable to create the dir, someone beat us to it?
				$i++;
			} else
				$bSuccess = true;
		} else {
			// Already exists, try another one
			$i++;
		}
	} while ($i < 1000 && !$bSuccess);
	
	if ($bSuccess) {
		// Store the new tmp path
		$sTmpPath .= $sRandom;
	} else {
		// In the unlikely situation that we kept colliding with other 
		return 2;
	}

	Config::SetPath("tmp", $sTmpPath);

	return 0;
}

/**
 * CleanupWork
 *
 * Deletes the temporary directory and all the associated files
 *
 * @return 0 on success
 */
function CleanupWork() {		
	$sTmpPath = Config::GetPath("tmp");

	// Delete contents of temp directory
	$aFiles = scandir($sTmpPath);
	
	foreach ($aFiles as $sFile) {
		if ($sFile == ".." || $sFile == ".")
			continue;
		
		if (!unlink($sTmpPath . "/" . $sFile)) {
			print("Unable to delete " . $sTmpPath . "/" . $sFile);
			return 1;
		}
	}
	if (!rmdir($sTmpPath)) {
		printf("Unable to delete tmp directory %s\n", $sTmpPath);
		return 2;
	}
	
	return 0;
}

/**
 * ProcessFile
 *
 * Takes a PDF and processes it and then adds it to the database
 *
 * @param sFile The complete filename (inc. path) to be processed
 * @param iSplit Split PDF after X pages, zero means auto detect
 *
 * @return 0 on success,
 *         1 if file could not be accessed
 *         2 if unable to split file into multiple
 *         3 if OCR fails
 *         4 if unable to add document to database
 *         5 if no pages were found
 */
function ProcessFile($sFile, $iSplit = 0) {
	$objDM = new DataMining();
	
	if (!file_exists($sFile) || !is_readable($sFile)) {
		printf("Unable to access \"%s\"\n", $sFile);
		return 1;
	}
	
	printf("Processing %s...\n", basename($sFile)); flush();
	
	
	// TODO: Use identify to see if a picture has content,
	// convert <filename> -colorspace Gray - | identify -format "%[standard-deviation.r]\n%[max.r]\n%[min.r]\n" -
	// std dev / max - min == %, if % < XX then no content (also make sure OCR concurs!)
	
	printf("  Pass 1: Extract PDF"); flush();
	// Start by splitting the file and counting pages
	$iPageCount = 0;
	$bRun = true;
	do {
		$sCmd = sprintf(
			"%s 2>&1 -density 300 -depth 8 \"%s\"[%d] %s/page%03d.tif",
			Config::GetTool("convert"),
			$sFile,
			$iPageCount,
			Config::GetPath("tmp"),
			$iPageCount);
		
		exec($sCmd, $aDummy, $iResult);
		if ($iResult == 0)
			$iPageCount++;
	} while ($iResult == 0);
	
	printf(", Found %d pages\n", $iPageCount); flush();
	
	if ($iPageCount == 0) {
		printf("Error! No pages found, aborting\n");
		return 5;
	}
	
	printf("  Pass 2: Search for multiple documents"); flush();

	$aDocuments = array();
	$aDocument = array();
	if ($iSplit == 0) {	
		// This is a cool thing, if we detect the special QR code, we can split
		// the document into multiple PDFs :)
		for ($i = 0; $i < $iPageCount; $i++) {
			$sCmd = sprintf(
				"%s 2>&1 %s/page%03d.tif",
				Config::GetTool("zbar"),
				Config::GetPath("tmp"),
				$i);
			
			unset($aResult);
			exec($sCmd, $aResult, $iResult);
			if ($iResult == 0) {
				// So, we found SOMETHING, lets see what exactly (we're very picky!)
				$iBarCodes = 0;
				// Count findings...
				foreach ($aResult as $sResult) {
					if ($sResult == sprintf("QR-Code:%s", $objDM->GetSeparatorText()))
						$iBarCodes++;
					if (preg_match('/scanned ([0-9]+) barcode/', $sResult, $aCount)) {
						$iBarTotal = intval($aCount[1]);
					}
				}
				// Compare to the tally
		 		if ($iBarCodes == $iBarTotal) {
					// Good stuff! Separator!
					if (!empty($aDocument))
						array_push($aDocuments, $aDocument);
					$aDocument = array();
				} else {
					// No separator, go to next
					array_push($aDocument, $i);
				}
			} else {
				// No barcode at all
				array_push($aDocument, $i);
			}
		}
	} else {
		// Split after every X page
		$c = 0;
		for ($i = 0; $i < $iPageCount; $i++) {
			array_push($aDocument, $i);
			$c++;
			if ($c == $iSplit) {
				$c = 0;
				array_push($aDocuments, $aDocument);
				$aDocument = array();
			}
		}
	}
	
	// Add potential straggler
	if (!empty($aDocument))
		array_push($aDocuments, $aDocument);
	
	$aFiles = array();
	if (count($aDocuments) > 1) {
		printf(", Found %d\n", count($aDocuments)); flush();
	
		printf("  Pass 2b: Splitting...\n"); flush();
		
		$iDocument = 0;
		foreach ($aDocuments as $aPages) {
			printf("    Document %d: ", $iDocument+1);
			flush();
			
			$sCmd = sprintf("%s %s cat", Config::GetTool("pdftk"), $sFile);
			foreach ($aPages as $sPage) {
				$sCmd .= " " . (intval($sPage) + 1);
			}
			$sTmpFile = sprintf("%s/subdoc%03d.pdf", Config::GetPath("tmp"), $iDocument);
			$sCmd .= sprintf(" output %s", $sTmpFile);
			exec($sCmd);
			if (!file_exists(sprintf("%s", $sTmpFile))) {
				printf("Unable to split document (\"%s\")\n", $sCmd);
				return 2;
			}
			$aFiles[$sTmpFile] = $aPages;
			
			printf("OK\n");
			
			$iDocument++;
		}
		
		// We can now delete the original (since we split it)
		unlink($sFile);
	} else {
		// Use original, since there isn't any multiples
		$aFiles = array($sFile => $aDocuments[0]);
		
		// Add linebreak so it looks nice :)
		printf("\n"); flush();
	}
	
	// Now, OCR the pages and get going
	printf("  Pass 3: OCR the pages\n"); flush();
	foreach ($aFiles as $sIgnore => $aPages) {
		foreach ($aPages as $iPage) {
			$sCmd = sprintf(
				"%s 2>&1 %s/page%03d.tif %s/page%03d -psm 1 -l " . Config::GetLanguage(), 
				Config::GetTool("ocr"),
				Config::GetPath("tmp"),
				$iPage,
				Config::GetPath("tmp"),
				$iPage);
			printf("    Page %d: ", $iPage + 1); flush();
			exec($sCmd, $aResult, $iResult);
			print_r($aResult);
			if ($iResult != 0) {
				printf("Failed OCR: \"%s\"\n", $sCmd);
				return 3;
			}
			print("OK\n"); flush();
		}
	}
	
	printf("  Pass 4: Adding document(s) to database\n"); flush();
	$i = 1;
	foreach ($aFiles as $sFile => $aPages) {
		printf("    Document %d: ", $i++); flush();
		if (!AddDocument($sFile, $aPages, $objDM)) {
			print("Failed\n");
			return 4;
		} else
			print("OK\n"); flush();
	}
	
	print("Done!\n"); flush();
	return 0;
}

function AddDocument($sFile, $aPages, $objDM) {
	// We need a UNIQUE name and directory for this file
	$sDir = strftime("%F/");
	$sDest = strftime("%H.%M.%S_document");
	
	// Create directory (if not already there)
	if (!is_dir(Config::GetPath("dest") . $sDir)) {
		if (!mkdir(Config::GetPath("dest") . $sDir, Config::GetPermission("dirmask"), false)) {
			printf("Failed to create directory \"%s\"\n", Config::GetPath("dest") . $sDir);
			return FALSE;
		} else {
			// Adjust the rights
			$iOld = error_reporting(E_ERROR);
			chmod(Config::GetPath("dest") . $sDir, Config::GetPermission("dirmask"));
			chgrp(Config::GetPath("dest") . $sDir, Config::GetPermission("group"));
			chown(Config::GetPath("dest") . $sDir, Config::GetPermission("user"));
			error_reporting($iOld);
		}
	}
	
	// Make sure we don't collide with existing filename
	// TODO: NOT THREAD SAFE!
	$i = 1;
	while (file_exists(Config::GetPath("dest") . $sDir . $sDest . $i . ".pdf"))
		$i++;
	
	// Final destination is...
	$sDest = Config::GetPath("dest") . $sDir . $sDest . $i . ".pdf";
	
	// Time to talk to mysql about this whole thing :)
	$db = mysql_pconnect(Config::getDB("host"), Config::getDB("username"), Config::getDB("password"));
	if (!$db) {
		printf("Cannot connect to database\n");
		return FALSE;
	}
	
	if (!mysql_select_db(Config::getDB("database"), $db)) {
		printf("Cannot open scanner database\n");
		return FALSE;
	}
	
	// Time to move the file AND add that into the database
	if (!rename($sFile, $sDest)) {
		printf("Couldn't move \"%s\" into \"%s\"!\n", $sFile, $sDest);
		return FALSE;
	}
	
	// Adjust the rights
	$iOld = error_reporting(E_ERROR);
	chmod($sDest, Config::GetPermission("filemask"));
	chgrp($sDest, Config::GetPermission("group"));
	chown($sDest, Config::GetPermission("user"));
	error_reporting($iOld);
	
	$SQL = sprintf("INSERT INTO documents (filename) VALUES ('%s')", $sDest);
	if (mysql_query($SQL, $db) === FALSE) {
		printf("Unable to add document to database: %s\n", mysql_error($db));
		return FALSE;
	}
	$iID = mysql_insert_id($db);
	
	// Finally, using the ID from the document, we add ALL the pages to it
	$sAllData = "";
	$sSplitter = uniqid(Config::GetSplitter(), true);
	$iPages = 0;
	
	foreach ($aPages as $iPage) {
		$sFile = sprintf("page%03d.txt", $iPage);
		
		$sContent = file_get_contents(Config::GetPath("tmp") . $sFile);
		
		if ($sContent !== FALSE) {
			$sAllData .= strtolower($sContent) . $sSplitter; // Space to avoid run-in
			$iPages++;
		} else {
			printf("Unable to load contents of \"%s\" into memory\n", Config::GetPath("tmp") . $sFile);
			return FALSE;
		}
	}
	
	// Save this data
	$SQL = sprintf(
		"INSERT INTO rawtext VALUES (%d, '%s', '%s')", 
		$iID, 
		mysql_real_escape_string($sAllData),
		mysql_real_escape_string($sSplitter));
	
	if (mysql_query($SQL, $db) === FALSE) {
		printf("Failed to insert data document %d: %s\n", $iID, mysql_error($db));
		return FALSE;
	}
	
	// Also update pagecount
	$SQL = sprintf("UPDATE documents SET pagecount = %d WHERE id = %d", $iPages, $iID);
	if (mysql_query($SQL, $db) === FALSE) {
		printf("Failed to update pagecount for %d: %s\n", $iID, mysql_error($db));
		return FALSE;
	}
	
	// Reformat the data
	$sAllData = str_replace($sSplitter, "\n", $sAllData);

	// Now for some magic, 
	// we try and guess the original date of the data
	$iDate = $objDM->GuessOriginalDate($sAllData);
	if ($iDate !== FALSE && $iDate != 0) {
		$SQL = sprintf("UPDATE documents SET dated = FROM_UNIXTIME(%d) WHERE id = %d", $iDate, $iID);
		$res = mysql_query($SQL, $db);
		if ($res === FALSE) {
			printf("ERROR! Failed to update document date: %s\n", mysql_error($db));
			return FALSE;
		}
	}

	// Finally, using the complete contents, we try and apply a category
	$res = mysql_query("SELECT * FROM categories", $db);
	if ($res === FALSE) {
		printf("WARNING: Was unable to get categories, defaults to unclassified\n");
		return TRUE;
	}
	
	$aResult = array();
	
	while (($aRes = mysql_fetch_array($res)) !== FALSE) {
		if (trim($aRes["keywords"]) == "")
			continue;
		
		$aWords = preg_split("/[\s,]*\\\"([^\\\"]+)\\\"[\s,]*|" . "[\s,]*'([^']+)'[\s,]*|" . "[\s,]+/", $aRes["keywords"], 0, PREG_SPLIT_NO_EMPTY | PREG_SPLIT_DELIM_CAPTURE);		
		
		// Count the occurance of the keywords in the document (case insensitive)
		$iHits = 0;
		foreach ($aWords as $sWord) {
			$bNegative = false;
			if ($sWord[0] == '-') {
				$bNegative = true;
				$sWord = substr($sWord, 1);
			}
			$iHit = substr_count($sAllData, $sWord);
			
			// If _ANY_ keyword fails, this isn't considered a hit at all
			if ( ($iHit > 0) == $bNegative) {
				$iHits = 0;
				break;
			}
			$iHits += $iHit;
		}
	
		if ($iHits != 0)
			array_push($aResult, array("id" => $aRes["id"], "hits" => $iHits));
	}
	
	if (!empty($aResult)) {
		//printf("%d categorie(s) matched\n", count($aResult));
		//print_r($aResult);
		$iHighest = 0;
		$aChosen = FALSE;
		foreach ($aResult as $aEntry) {
			if ($aEntry["hits"] > $iHighest) {
				$iHighest = $aEntry["hits"];
				$aChosen = $aEntry;
			}
		}
		
		//printf("  Category %d was chosen due to highest hits.\n", $aChosen["id"]);
		
		$SQL = sprintf("UPDATE documents SET category = %d WHERE id = %d", $aChosen["id"], $iID);
		$res = mysql_query($SQL, $db);
		if ($res === FALSE) {
			printf("ERROR! Failed to update document category: %s\n", mysql_error($db));
			return FALSE;
		}
	}
	
	return TRUE;
}

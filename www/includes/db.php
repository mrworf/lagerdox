<?php

require_once("datamining.php");
require_once("config.php");

class ScannerDB {
	var $db;
	var $dm;

	function open() {
		$this->db = mysql_pconnect(Config::GetDB("host"), Config::GetDB("username"), Config::GetDB("password"));
		if ($this->db !== FALSE) {
			mysql_select_db(Config::GetDB("database"), $this->db);
		}

		$this->dm = new DataMining();
	}

	/**
	 * Retreives the $iCount number of documents, newest first unless $bReversed
	 *
	 * Returns the content as array
	 */
	function ListDocuments($iCount, $bReversed, $bUseDated) {
		if ($iCount < 1)
			return FALSE;

		$SQL = sprintf("
			SELECT 
				documents.id AS id, 
				categories.name AS name, 
				UNIX_TIMESTAMP(documents.added) AS added,
				UNIX_TIMESTAMP(documents.dated) AS dated,
				documents.filename AS filename,
				documents.pagecount AS pages
			FROM documents 
				LEFT JOIN categories 
					ON (documents.category = categories.id) 
				LEFT JOIN rawtext 
					ON (rawtext.document = documents.id)
			ORDER BY documents.%s %s 
			LIMIT %d", 
		$bUseDated ? "dated" : "added",
		$bReversed ? "" : "DESC", 
		$iCount);

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;

		$aResult = array();
		while (($aRecord = mysql_fetch_array($res)) !== FALSE)
			array_push($aResult, $aRecord);

		return $aResult;
	}

	function ListDocumentsByCategory($iCount, $iCategory, $bReversed, $bUseDated) {
		if ($iCount < 1)
			return FALSE;

		$SQL = sprintf("
			SELECT 
				documents.id AS id, 
				categories.name AS name, 
				UNIX_TIMESTAMP(documents.added) AS added,
				UNIX_TIMESTAMP(documents.dated) AS dated,
				documents.filename AS filename,
				documents.pagecount AS pages
			FROM documents 
				LEFT JOIN categories 
					ON (documents.category = categories.id) 
				LEFT JOIN rawtext 
					ON (rawtext.document = documents.id)
			WHERE
				documents.category = %d
			ORDER BY documents.%s %s
			LIMIT %d",
			intval($iCategory),
			$bUseDated ? "dated" : "added",
			$bReversed ? "" : "DESC", 
			intval($iCount));

		//die($SQL);

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;
		
		$aResult = array();
		while (($aRecord = mysql_fetch_array($res)) !== FALSE)
			array_push($aResult, $aRecord);
			
		return $aResult;
	}
	
	/**
	 * Will generate a thumbnail for a given document
	 */
	function ShowThumbnail($iID, $iPage, $iWidth) {
		$SQL = "SELECT documents.filename AS filename, documents.pagecount AS pages FROM documents LEFT JOIN rawtext ON (rawtext.document = documents.id) WHERE id = " . $iID;
		
		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;
		
		$aRes = mysql_fetch_array($res);
		if ($aRes === FALSE)
			return FALSE;

		if ($iPage < 1 || $iPage > $aRes["pages"])
			return FALSE;

		// Split the thumbs off into their own directory
		$sFilename = $aRes["filename"];
		$sPath = dirname($sFilename);
		$sFile = basename($sFilename);
		
		// Create thumb directory
		if (!file_exists($sPath . "/thumbs")) {
			if (!mkdir($sPath . "/thumbs")) {
				return FALSE;
			}
			chgrp($sPath . "/thumbs", Config::getPermission("group"));
			chmod($sPath . "/thumbs", Config::getPermission("dirmask"));
		}

		$sThumbnail = sprintf("%s/thumbs/%s-%d-%d.png", $sPath, $sFile, $iWidth, $iPage);
		
		if (!file_exists($sThumbnail)) {
			// File doesn't exist, we need to generate one
			$sPrefix = uniqid();
			/*
			$sCmd = sprintf("/usr/bin/pdfimages -f %d -l %d %s /tmp/%s", $iPage, $iPage, $sFilename, $sPrefix);
			exec($sCmd);
			$sCmd = sprintf("/usr/bin/convert /tmp/%s-000.ppm -resize %dx %s", $sPrefix, $iWidth, $sThumbnail);
			exec($sCmd);
			*/
			$sCmd = sprintf("/usr/bin/convert 2>&1 -depth 8  %s[%d] -resize %dx %s", $sFilename, $iPage-1, $iWidth, $sThumbnail);
			exec($sCmd);
			//unlink(sprintf("/tmp/%s-000.ppm", $sPrefix));
			
			chgrp($sThumbnail, Config::getPermission("group"));
			chmod($sThumbnail, Config::getPermission("filemask"));
		}
		readfile($sThumbnail);
	}
	
	function GetDetails($iID) {
		// $SQL = "SELECT documents.*, UNIX_TIMESTAMP(documents.added) AS added, UNIX_TIMESTAMP(documents.dated) as dated, categories.name AS name, documents.pagecount AS pages FROM documents LEFT JOIN categories ON (categories.id = documents.category) LEFT JOIN rawtext ON (rawtext.document = documents.id) WHERE documents.id = " . $iID;
		$SQL = "SELECT documents.*, UNIX_TIMESTAMP(documents.added) AS added, UNIX_TIMESTAMP(documents.dated) as dated, categories.name AS name, documents.pagecount AS pages FROM documents LEFT JOIN categories ON (categories.id = documents.category) WHERE documents.id = " . $iID;

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;
		
		$aRes = mysql_fetch_array($res);
			
		return $aRes;
	}

	function GetRawText($iID) {
		$SQL = "SELECT * FROM rawtext WHERE document = " . $iID;

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;
		
		$aRes = mysql_fetch_array($res);
		if ($aRes !== FALSE && !empty($aRes))
			return $aRes["content"];
		else
			return FALSE;
	}
	
	function TranslateDate($iDate, $bIncludeTime = true) {
		$iTime = intval($iDate);
		$sTimeSuffix = ", %I:%M:%S %P";
		if (!$bIncludeTime)
			$sTimeSuffix = "";

		if (strftime("%F", $iTime) == strftime("%F"))
			$sTime = strftime("Today" . $sTimeSuffix, $iTime);
		else if (strftime("%F", $iTime) == strftime("%F", time() - 86400))
			$sTime = strftime("Yesterday" . $sTimeSuffix, $iTime);
		else if (strftime("%Y", $iTime) == strftime("%Y"))
			$sTime = strftime("%a, %e %b" . $sTimeSuffix, $iTime);
		else if ($iTime == 0)
			$sTime = "Unknown";
		else
			$sTime = strftime("%e %b %Y" . $sTimeSuffix, $iTime);
			
		return $sTime;
	}
	
	function TranslateFilesize($iRawsize) {
		$sSuffix = "bytes";
		$iDivide = 1;
		
		if ($iRawsize > 1048575) {
			$sSuffix = "MB";
			$iDivide = 1048576;
		} else if ($iRawsize > 1023) {
			$sSuffix = "KB";
			$iDivide = 1024;
		}
		
		return number_format($iRawsize / $iDivide, 1, ".", " ") . " " . $sSuffix;
	}
	
	function Delete($iID) {
		// First, get the details for easier deletion
		$aRes = $this->GetDetails($iID);
		if ($aRes === FALSE)
			return;
		
		$SQL = sprintf("
			DELETE 
			FROM documents
			WHERE id = %d",
			$aRes["id"]);
			
		mysql_query($SQL, $this->db);
		
		$SQL = sprintf("
			DELETE 
			FROM rawtext
			WHERE document = %d",
			$aRes["id"]);

		mysql_query($SQL, $this->db);

		// Time to remove the actual document
		$sCmd = sprintf("rm %s", $aRes["filename"]);
		exec($sCmd);		

		$sPath = dirname($aRes["filename"]);
		$sFile = basename($aRes["filename"]);

		$sThumbnail = sprintf("%s/thumbs/%s-*.png", $sPath, $sFile);

		$sCmd = sprintf("rm %s %s", $aRes["filename"], $sThumbnail);
		exec($sCmd);		
	}

	/**
	 * Add a range keyword to a SQL statement
	 *
	 * @param sField The database field to apply it to
	 * @param sFunction Which SQL function to apply to the field (if any)
	 * @param sValue The query
	 * @param iMin Minimum allowed value of sValue
	 * @param iMax Maximum allowed value of sValue
	 *
	 * @return Partial SQL statement or FALSE if invalid input
	 */
	function ranged($sField, $sFunction, $sValue, $iMin, $iMax) {
		if (!preg_match('/([0-9]*)(\-{0,1})([0-9]*)/', $sValue, $aItems))
			return FALSE;

		$sRes = FALSE;

		$iVal1 = FALSE;
		$iVal2 = FALSE;
		$bRange = FALSE;

		if ($aItems[1] != "")
			$iVal1 = intval($aItems[1]);
		if ($aItems[3] != "")
			$iVal2 = intval($aItems[3]);
		if ($aItems[2] != "")
			$bRange = TRUE;

		if ($iVal1 !== FALSE && $iVal2 !== FALSE) {
			if ($iVal1 > $iVal2) {
				$iTmp = $iVal1;
				$iVal1 = $iVal2;
				$iVal2 = $iTmp;
			}
		}
		
		if ($iVal1 !== FALSE && ($iVal1 > $iMax || $iVal1 < $iMin) || $iVal2 !== FALSE && ($iVal2 > $iMax || $iVal2 < $iMin))
			return FALSE;
		
		if ($bRange && $iVal1 === FALSE && $iVal2 !== FALSE) { // <=
			$sRes = sprintf("%s(%s) <= %d", $sFunction, $sField, $iVal2);
		} else if ($bRange && $iVal1 !== FALSE && $iVal2 === FALSE) { // >=
			$sRes = sprintf("%s(%s) >= %d", $sFunction, $sField, $iVal1);
		} else if ($bRange && $iVal1 !== FALSE && $iVal2 !== FALSE) { // XX - YY
			$sRes = sprintf("(%s(%s) <= %d AND %s(%s) >= %d)", $sFunction, $sField, $iVal2, $sFunction, $sField, $iVal1);
		} else if (!$bRange && $iVal1 !== FALSE) { // ==
			$sRes = sprintf("%s(%s) = %d", $sFunction, $sField, $iVal1);
		}
		
		return $sRes;
	}

	function Search($sKeywords) {
		$sError = "";
		$sKeywords = trim($sKeywords);
		
		if ($sKeywords == "")
			return array();
		
		// Get the words so we can feed it to the database
		$aWords = preg_split("/[\s,]*\\\"([^\\\"]+)\\\"[\s,]*|" . "[\s,]*'([^']+)'[\s,]*|" . "[\s,]+/", $sKeywords, 0, PREG_SPLIT_NO_EMPTY | PREG_SPLIT_DELIM_CAPTURE);
		
		$sWhere = "";
		foreach ($aWords as $sWord) {
			// Handle negative queries
			$bNegative = false;
			$sNegate = "";
			if ($sWord[0] == '-') {
				$bNegative = true;
				$sNegate = "NOT";
				$sWord = substr($sWord, 1);
			}
			
			// Keyword handling
			if (preg_match('/([^:]+):(.+)/i', $sWord, $aResult)) {
				// Keyword?
				$sOption = $aResult[2];
				$sKeyword = strtolower($aResult[1]);
				switch($sKeyword) {
					case "category":
						$sWord = "";
						$sWhere .= sprintf(" AND %s name LIKE '%%%s%%'", $sNegate, $sOption);
						break;
					
					case "pages":
						$sWord = "";
						$sRange = $this->ranged("documents.pagecount", "", $sOption, 1, 99999999);
						if ($sRange === FALSE)
							$sError .= ", page query incorrect";
						else
							$sWhere .= sprintf(" AND %s %s", $sNegate, $sRange);
						break;
					
					case "year":
						$sWord = "";
						$sRange = $this->ranged("documents.dated", "YEAR", $sOption, 1899, 9999);
						if ($sRange === FALSE)
							$sError .= ", year query incorrect";
						else
							$sWhere .= sprintf(" AND %s %s", $sNegate, $sRange);
						break;
						
					case "month":
						$sWord = "";
						$sRange = $this->ranged("documents.dated", "MONTH", $sOption, 1, 12);
						if ($sRange === FALSE)
							$sError .= ", month query incorrect";
						else
							$sWhere .= sprintf(" AND %s %s", $sNegate, $sRange);
						break;

					case "day":
						$sWord = "";
						$sRange = $this->ranged("documents.dated", "DAY", $sOption, 1, 31);
						if ($sRange === FALSE)
							$sError .= ", day query incorrect (please use 1-31 values)";
						else
							$sWhere .= sprintf(" AND %s %s", $sNegate, $sRange);
						break;

					case "scan_year":
						$sWord = "";
						$sRange = $this->ranged("documents.added", "YEAR", $sOption, 1899, 9999);
						if ($sRange === FALSE)
							$sError .= ", scan_year query incorrect";
						else
							$sWhere .= sprintf(" AND %s %s", $sNegate, $sRange);
						break;
						
					case "scan_month":
						$sWord = "";
						$sRange = $this->ranged("documents.added", "MONTH", $sOption, 1, 12);
						if ($sRange === FALSE)
							$sError .= ", scan_month query incorrect";
						else
							$sWhere .= sprintf(" AND %s %s", $sNegate, $sRange);
						break;

					case "scan_day":
						$sWord = "";
						$sRange = $this->ranged("documents.added", "DAY", $sOption, 1, 31);
						if ($sRange === FALSE)
							$sError .= ", scan_day query incorrect (please use 1-31 values)";
						else
							$sWhere .= sprintf(" AND %s %s", $sNegate, $sRange);
						break;
				}
			}
			
			if ($sWord != "")
				$sWhere .= sprintf(" AND %s (rawtext.content LIKE '%%%s%%')", $sNegate, mysql_real_escape_string($sWord));
		}
		$sWhere = substr($sWhere, 5);
		
		$SQL = sprintf("
			SELECT 
				documents.id AS id, 
				categories.name AS name, 
				UNIX_TIMESTAMP(documents.added) AS added,
				UNIX_TIMESTAMP(documents.dated) AS dated,
				documents.filename AS filename,
				documents.pagecount AS pages
			FROM rawtext 
				LEFT JOIN documents
					ON (rawtext.document = documents.id)
				LEFT JOIN categories 
					ON (documents.category = categories.id) 
			WHERE 
				%s
			ORDER BY
				documents.dated
			",
			$sWhere
			);

		//die($SQL);

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE) {
			die("<pre>$SQL</pre>" . "<hr>$sError<hr>" . mysql_error($this->db));
			return FALSE;
		}
		
		$aResult = array();
		while (($aRecord = mysql_fetch_array($res)) !== FALSE)
			array_push($aResult, $aRecord);
			
		return $aResult;
	}

	function GetCategories() {
		$SQL = "
			SELECT 
				categories.id AS id,
				categories.name AS name,
				categories.keywords AS keywords,
				COUNT(documents.id) AS inuse
			FROM 
				categories
				LEFT JOIN documents
					ON (documents.category = categories.id)
			GROUP BY
				categories.id
			ORDER BY
				categories.name";
		
		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;
		
		$aResult = array();
		while (($aRecord = mysql_fetch_array($res)) !== FALSE)
			array_push($aResult, $aRecord);
			
		return $aResult;
	}
	
	function UpdateCategory($id, $sName, $sKeywords, $bRemoveLink) {
		$SQL = sprintf("
			UPDATE
				categories
			SET
				name = '%s',
				keywords = '%s'
			WHERE
				id = %d",
			mysql_real_escape_string($sName),
			mysql_real_escape_string($sKeywords),
			$id);
			
		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return false;
		
		if ($bRemoveLink) {
			$SQL = sprintf("
				UPDATE
					documents
				SET
					category = 0
				WHERE
					category = %d",
				$id);

			$res = mysql_query($SQL, $this->db);
			if ($res === FALSE)
				return false;
		}

		return true;		
	}

	function AddCategory($sName, $sKeywords) {
		$SQL = sprintf("
			INSERT INTO
				categories
			(name, keywords)
			VALUES
			('%s', '%s')", 
			mysql_real_escape_string($sName),
			mysql_real_escape_string($sKeywords),
			$id);
			
		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return false;
		
		return true;		
	}

	function DeleteCategory($id) {
		$SQL = sprintf("
			DELETE FROM
				categories
			WHERE
				id = %d",
			$id);
			
		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return false;
		
		$SQL = sprintf("
			UPDATE
				documents
			SET
				category = 0
			WHERE
				category = %d",
			$id);

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return false;

		return true;		
	}

	function UpdateDocumentCategory($id, $newcat) {
		// First, make sure it EXISTS!
		$aCat = $this->GetCategories();
		$bFound = false;
		foreach ($aCat as $aEntry) {
			if ($aEntry["id"] == $newcat) {
				$bFound = true;
				break;
			}
		}
		if (!$bFound)
			return FALSE;
		
		$SQL = sprintf("
			UPDATE
				documents
			SET
				category = %d
			WHERE
				id = %d",
			$newcat,
			$id);
			
		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return false;
		
		return true;		
	}

	function UpdateDocumentDate($id, $iDate) {
		$SQL = sprintf("
			UPDATE
				documents
			SET
				dated = FROM_UNIXTIME(%d)
			WHERE
				id = %d",
			intval($iDate),
			$id);

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE || mysql_affected_rows($this->db) == 0) {
			return false;
		}

		return true;
	}

	function GuessDateForDocument($id, $iScanDate = FALSE) {
		$SQL = sprintf("SELECT * FROM rawtext WHERE document = %d", $id);

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;

		$sData = "";
		while (($aRes = mysql_fetch_array($res)) !== FALSE) {
			$sData .= $aRes["content"] . "\n";
		}

		return $this->dm->GuessOriginalDate($sData, $iScanDate);
	}

	function GuessCategoryForDocument($id) {
		$SQL = sprintf("SELECT * FROM rawtext WHERE document = %d", $id);

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;

		$sData = "";
		while (($aRes = mysql_fetch_array($res)) !== FALSE) {
			$sData .= $aRes["content"] . "\n";
		}
		
		// Fetch all categories
		$res = mysql_query("SELECT * FROM categories", $this->db);
		if ($res === FALSE) {
			return FALSE;
		}

		$aCat = array();
		
		while (($aRes = mysql_fetch_array($res)) !== FALSE) {
			array_push($aCat, $aRes);
		}

		return $this->dm->GuessCategory($sData, $aCat);
	}

	function GetTimeline($iYear = FALSE, $bScanDate = FALSE) {
		$sField = $bScanDate ? "added" : "dated";
		
		if ($iYear === FALSE) {
			$SQL = sprintf('
				SELECT COUNT(id) AS entries, UNIX_TIMESTAMP(DATE_FORMAT(%s, "%%Y-%%m-01")) AS dated 
				FROM documents 
				GROUP BY DATE_FORMAT(%s, "%%Y-%%m") 
				ORDER BY %s
			', $sField, $sField, $sField);
		} else {
			$SQL = sprintf('
				SELECT COUNT(id) AS entries, UNIX_TIMESTAMP(%s) AS dated
				FROM documents
				WHERE DATE_FORMAT(dated, "%%Y") == %d
				GROUP BY %s
				ORDER BY %s
			', $sField, $iYear, $sField, $sField);
		}
		
		//die($SQL);

		$res = mysql_query($SQL, $this->db);
		if ($res === FALSE)
			return FALSE;

		$aData = array();
		while (($aRes = mysql_fetch_array($res)) !== FALSE) {
			array_push($aData, $aRes);
		}

		return $aData;
	}

};

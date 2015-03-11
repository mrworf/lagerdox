<?php

class DataMining {
	var $sQRCodeText = "__SCANNER_DOCUMENT_SEPARATOR__";
	
	function GetSeparatorText() {
		return $this->sQRCodeText;
	}
	
	function GenerateSeparator() {
			$sTmp = sprintf("/tmp/%s.png", uniqid());
			$sCmd = sprintf("/usr/bin/qrencode -o %s \"%s\"", $sTmp, $this->sQRCodeText);
			exec($sCmd);
			$sCmd = sprintf("
				/usr/bin/convert -size 1237x1762 xc:white \
				%s -gravity NorthWest -composite \
				%s -gravity North -composite \
				%s -gravity NorthEast -composite \
				%s -gravity West -composite \
				%s -gravity Center -composite \
				%s -gravity East -composite \
				%s -gravity SouthWest -composite \
				%s -gravity South -composite \
				%s -gravity SouthEast -composite \
				-pointsize 25 \
				-gravity Center -draw \"text 0,-75 'Scan Once'\" \
				-gravity Center -draw \"text 0,75 'Split Many'\" \
				+clone \
				pdf:-",
			$sTmp, 
			$sTmp, 
			$sTmp, 
			$sTmp, 
			$sTmp, 
			$sTmp, 
			$sTmp, 
			$sTmp, 
			$sTmp
			);
			passthru($sCmd);
			unlink($sTmp);
	}

	function GuessOriginalDate($sData, $iScanDate = FALSE, $bDebug = FALSE) {
		$aMonths = array("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec");
		// List of month, using the last unique bits to try and piece together it, incase OCR failed badly
		$aMonthsLast = array("nuary", "ruary", "rch", "ril", "may", "une", "uly", "ust", "tember", "ober", "vember", "cember");
		$aDates = array();
		// Time to scrape the text for dates
		preg_match_all('@([ o01]?[o0-9][/\\-\\.~][o0123]?[o0-9][/\\-\\.~][12]?[0-9]?[oiz0-9] ?[oiz0-9])@', $sData, $aResult);
		if (isset($aResult[1]) && !empty($aResult[1]))
			$aDates = array_merge($aDates, $aResult[1]);
		//$sData = "july 31  2012";
		preg_match_all('@((?:' . implode("|", $aMonthsLast) . '|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|july|August|September|october|November|December) +[0-3]?[ 0-9]{1,2}[\\., ]+[12][0-9 ]{3,4})@i', $sData, $aResult);
		if (isset($aResult[1]) && !empty($aResult[1])) {
			$aDates = array_merge($aDates, $aResult[1]);
		}
		// DD MMMMMMMM YYYY
		preg_match_all('@([0-3]?[ 0-9]{1,2}[\\.\\-, ]+(?:' . implode("|", $aMonthsLast) . '|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|july|August|September|october|November|December)[\\.\\-, ]+[12][0-9 ]{3,4})@i', $sData, $aResult);
		if (isset($aResult[1]) && !empty($aResult[1])) {
			$aDates = array_merge($aDates, $aResult[1]);
		}
		// This one is weird, because it's when we have MMM DD HH:MM:SS YYYY
		preg_match_all('@((?:' . implode("|", $aMonthsLast) . '|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|july|August|September|october|November|December) +[0-3]?[0-9][\\., ]+[0-9\\?:]{5,8} +[12][0-9 ]{3,4})@i', $sData, $aResult);
		if (isset($aResult[1]) && !empty($aResult[1])) {
			$aDates = array_merge($aDates, $aResult[1]);
		}

		if ($bDebug) print_r($aResult);

		// Time to do some conversion here
		$aList = array();
		$aConvert = array("o" => "0",
		                  "z" => "2",
		                  "i" => "1");
		foreach ($aDates as $sDate) {
			// Clean it
			$sDate = trim(strtolower($sDate));
			$sDateClean = strtr($sDate, $aConvert);

			$aBits = preg_split('@[\s,\\.\\-/~]+@', $sDate);
			$aBitsClean = preg_split('@[\s,\\.\\-/~]+@', $sDateClean);

			if ($bDebug) print_r($aBits);

			// There is a special case, if we get 4 items and the last two are 3 and 1, then join them
			if (count($aBits) == 4 && strlen($aBits[2]) == 3 && strlen($aBits[3]) == 1)
				$aBits[2] .= $aBits[3];
			else if (count($aBits) == 4 && (strlen($aBits[2]) == 2 || strlen($aBits[2]) == 4)) {
				// Looks like a MM DD YY(YY) version
				unset($aBits[3]);
			} else if (count($aBits) == 4 && strlen($aBits[1]) == 1 && strlen($aBits[2]) == 1 && (strlen($aBits[3]) == 2 || strlen($aBits[3]) == 4)) {
				// Looks like a MM D D YY(YY) version, merge bits 2 into 1
				$aBits[1] .= $aBits[2];
				$aBitsClean[1] .= $aBitsClean[2];
				$aBits[2] = $aBits[3];
				$aBitsClean[2] = $aBitsClean[3];
				unset($aBits[3]);
				unset($aBitsClean[3]);
			} else if (count($aBits) == 4 && (strlen($aBits[2]) > 4 || strlen($aBits[2]) == 4)) {
				// Looks like a MM DD HH:MM:SS YY(YY) version
			} else if (count($aBits) != 3) { // If the bits aren't three, then it's not a date!
				if ($bDebug) print("skipping since it's not a date\n");
				continue;
			}
			
			if ($bDebug) print_r($aBits);

			$iTime = 0;
			if (is_numeric($aBits[0]) && is_numeric($aBits[1]) && is_numeric($aBits[2])) {
				// It's a completely numeric date. We're assuming it's a US date (MM DD YYYY)
				$iTime = mktime(0, 0, 0, $aBits[0], $aBits[1], $aBits[2]);
			} else if (is_numeric($aBitsClean[0]) && is_numeric($aBitsClean[1]) && is_numeric($aBitsClean[2])) {
				$iTime = mktime(0, 0, 0, $aBitsClean[0], $aBitsClean[1], $aBitsClean[2]);
			} else if (is_numeric($aBitsClean[0]) && !is_numeric($aBitsClean[1]) && is_numeric($aBitsClean[2])) {
				// Uses text, assuming DD MMM(MMM) YYYY
				$iMonth = 0;
				for ($i = 0; $i != count($aMonths); ++$i) {
					if (substr($aBits[0], 0, 3) == $aMonths[$i] ||
					    substr($aBits[0], -strlen($aMonthsLast[$i])) == $aMonthsLast[$i]) {
					    	$iMonth = $i;
					}
				}
				if ($iMonth === FALSE)
					continue;

				$iTime = mktime(0, 0, 0, $iMonth+1, $aBitsClean[0], $aBitsClean[2]);
			} else {
				// Uses text, assuming MMM(MMM) DD YYYY
				$iMonth = 0;
				for ($i = 0; $i != count($aMonths); ++$i) {
					if (substr($aBits[0], 0, 3) == $aMonths[$i] ||
					    substr($aBits[0], -strlen($aMonthsLast[$i])) == $aMonthsLast[$i]) {
					    	$iMonth = $i;
					}
				}
				if ($iMonth === FALSE)
					continue;
					
				// One more exception here, if the last bit is 4 and the second to last is more than 4, use last for year
				if (strlen($aBitsClean[2]) > 4 && strlen($aBitsClean[3]) == 4)
					$iTime = mktime(0, 0, 0, $iMonth+1, $aBitsClean[1], $aBitsClean[3]);
				else
					$iTime = mktime(0, 0, 0, $iMonth+1, $aBitsClean[1], $aBitsClean[2]);
			}
			array_push($aList, $iTime);
		}
		
		if ($bDebug) {
			print_r($aDates);
			print_r($aList);
		}

		/**
		 * For now, we calculate the distance in days and choose
		 * the entry which is closest to todays (or scanned) date, based on the
		 * fact that usually you don't get future dated stuff :)
		 **/
		if ($iScanDate === FALSE)
			$iNow = time();
		else
			$iNow = $iScanDate;
				
		// Make sure we strip off the time part to avoid issues with "rounding"
		$iNow = mktime(0, 0, 0, date("n", $iNow), date("j", $iNow), date("Y", $iNow));
		$iClosest = 0;
		foreach ($aList as $iDate) {
			if ($bDebug) printf("Testing %d ... ", $iDate);
			// Avoid future dating things...
			if ($iDate > $iNow) {
				if ($bDebug) printf("Future! Skip!\n");
				continue;
			}
				
			if (abs($iNow - $iDate) < abs($iNow - $iClosest)) {
				if ($bDebug) printf("Found good match!\n");
				$iClosest = $iDate;
			} else
				if ($bDebug) printf("Not closer, skipping\n");
		}

		// Check the final delta, because we are kinda picky
		if (abs(date("Y", $iNow) - date("Y", $iClosest)) > 9) {
			// Over 9 years delta, probably not a valid guess!
			if ($bDebug) printf("Selected match differs with more than 9 years (%d, %s), abort!\n", $iClosest, date("d M Y", $iClosest));
			return FALSE;
		}

		if ($bDebug) printf("Closest match is: %d (%s)\n", $iClosest, date("d M Y", $iClosest));

		return $iClosest;
	}

	function GuessCategory($sData, $aCategory) {
		$aResult = array();
		
		foreach ($aCategory as $aRes) {
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
				$iHit = substr_count($sData, $sWord);
				
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
			return $aChosen["id"];
		}

		return 0;
	}

};
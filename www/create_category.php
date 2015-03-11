<?php
require_once("includes/db.php");

function filter_words($sWord) {
	//return TRUE;
	
	// Remove non-likely words
	if (preg_match('/[^a-z0-9]/', $sWord))
		return FALSE;
	// Make sure we have atleast 3 characters
	if (strlen($sWord) < 3)
		return FALSE;
		
	// No more than 3 consonants in a row
	if (preg_match('/[bcdfghjklmnpqrstvwxz]{4,}/', $sWord))
		return FALSE;
	// No more than 3 vowels in a row
	if (preg_match('/[aeiouy]{4,}/', $sWord))
		return FALSE;
		
	return TRUE;
}

function obtainData($objDb, $id) {
	$aRes = $objDb->GetDetails($id);
	$sText = $objDb->GetRawText($id);
	if ($aRes === FALSE || $sText === FALSE) {
		// No such record!
		return FALSE;
	}

	// Clean up list of words
	$aWords = array_filter(array_unique(str_word_count($sText, 1)), "filter_words");

	// Split words into likely and unlikely (based on spelling)
	$aLikely = array();
	$aUnlikely = array();
	
	$hSpell = pspell_new("en");
	if ($hSpell !== FALSE) {
		foreach ($aWords as $sWord) {
			// Make a spellcheck on it
			if (pspell_check($hSpell, $sWord))
				array_push($aLikely, $sWord);
			else
				array_push($aUnlikely, $sWord);
		}
	} else
		$aLikely = $aWords;
		
	return array("likely" => $aLikely, "unlikely" => $aUnlikely);
}	

	if (isset($_GET["id"])) {
		// Convert!
		$aBatch = array($_GET["id"]);
	} else if (isset($_POST["batch"])) {
		$aBatch = $_POST["batch"];
	} else {
		header("Location: index.php");
		exit;
	}

	$objDb = new ScannerDB();
	$objDb->open();

	// Iterate through the data (this should probably display a progressbar
	// in the browser, since the user can select a gazillion files.
	$aItems = array();

	$aCombLikely = FALSE;
	$aCombUnlikely = FALSE;
	
	foreach ($aBatch as $id) {
		$aRes = obtainData($objDb, $id);
		if ($aRes !== FALSE) {
			array_push($aItems, array("id" => $id, "likely" => $aRes["likely"], "unlikely" => $aRes["unlikely"]));
			
			if ($aCombLikely === FALSE) {
				$aCombLikely = $aRes["likely"];
				$aCombUnlikely = $aRes["unlikely"];
			} else {
				$aCombLikely = array_unique(array_merge($aCombLikely, $aRes["likely"]));
				$aCombUnlikely = array_unique(array_merge($aCombUnlikely, $aRes["unlikely"]));
			}
		}
		$aRes = NULL;
	}

	// So we have all the words and an intersect, but that isn't enough, count the number of times
	// that words are used, ie, rank them
	$aCombLikely = array_flip(array_unique($aCombLikely));
	$aCombUnlikely = array_flip(array_unique($aCombUnlikely));

	// Reset
	foreach ($aCombLikely as $key => $value)
		$aCombLikely[$key] = array("count" => 0, "ids" => array());
	foreach ($aCombUnlikely as $key => $value)
		$aCombUnlikely[$key] = array("count" => 0, "ids" => array());

	// Ranking
	foreach ($aItems as $aItem) {
		foreach ($aItem["likely"] as $needle) {
			if (isset($aCombLikely[$needle]))
				$aCombLikely[$needle]["count"]++;
				array_push($aCombLikely[$needle]["ids"], $aItem["id"]);
		}
	}
	arsort($aCombLikely);

	foreach ($aItems as $aItem) {
		foreach ($aItem["unlikely"] as $needle) {
			if (isset($aCombUnlikely[$needle]))
				$aCombUnlikely[$needle]["count"]++;
				array_push($aCombUnlikely[$needle]["ids"], $aItem["id"]);
		}
	}
	arsort($aCombUnlikely);

?>
<html>
	<head>
		<title>Create category from document</title>
		<style type="text/css">
			img {
				margin: 5px;
				border: 1px solid;
			}
			
			a {
				margin: 2px;
				padding: 0px 2px 0px 2px;
			}
			
			a.active {
				margin: 1px;
				padding: 0px 2px 0px 2px;
				border: 1px solid black;
			}
			
			img {
				opacity:1;
			}
			
			img.hidden {
				opacity:0.1;
			}
		</style>
		
		<script type="text/javascript">
			var refCounter = new Array();
			
			function toggle(obj, sList) {
				var sIDs = sList.split(",");
				var state = 0;
				
				if (obj.className == "") {
					obj.className = "active";
					state = 1;
				} else {
					obj.className = "";
					state = -1;
				}
				
				for (var i = 0; i != sIDs.length; ++i) {
					if (isNaN(refCounter["doc" + sIDs[i]]))
						refCounter["doc" + sIDs[i]] = 0;
					refCounter["doc" + sIDs[i]] += state;
					
					// Failsafe incase of stupid bugs
					if (refCounter["doc" + sIDs[i]] < 0)
						refCounter["doc" + sIDs[i]] = 0;
				}
				
				updateImages();
			}
			
			function updateImages() {
				for (var ref in refCounter) {
					var obj = document.getElementById(ref);
					obj.className = (refCounter[ref] > 0) ? "" : "hidden";
				}
			}
		</script>
	</head>
	<body>
		<a href="index.php">Back to front page</a><hr/>
		<h1>Create category from document</h1>

	<?php
		// Calculate amount of color differance based on
		// the number of analyzed documents
		$iMax = count($aBatch);
		$iStep = 255 / ($iMax);
	
		$i = 0;
		$iColor = 0;
		foreach ($aCombLikely as $key => $aData) {
			$value = $aData["count"];
			if ($value < 2 && count($aBatch) > 1)
				break;

			if ($i == 0 || $i != $value) {
				if ($i != 0)
					print('</span> - ');
				printf('<span style="background-color: #%02x%02x%02x">', 0xFF - (($value) * $iStep), 0xFF - ((($iMax - $value)/3) * $iStep), 0);
			} else
				print(" ");

			printf('<a href="javascript:void(0);" onclick="toggle(this, %s)">%s</a>', "'" . implode(",", $aData["ids"]) . "'", $key);
			$i = $value;
		}
		print('</span>');
	?>
	<hr/>
	<?php
		// We need to visualize the results ... urgh
		foreach ($aItems as $aItem) {
			printf('<img id="doc%d" src="thumb.php?id=%d&width=100" alt="thumbnail" class="hidden"/>', $aItem["id"], $aItem["id"]);
		}
	?>
	</body>
</html>

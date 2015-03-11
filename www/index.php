<?php
 
require_once("includes/db.php");

function last10($objDb, $bDated = false) {
	$aRes = $objDb->ListDocuments(20, false, $bDated);
	
	display_results($aRes, $objDb);
}

function category($objDb, $id) {
	$aRes = $objDb->ListDocumentsByCategory(101, $id, false, true);
	
	display_results($aRes, $objDb);
}

function display_results($aRes, $objDb) {
	if ($aRes === FALSE) {
		printf('<div class="error">Unable to access database</div>');
		return;
	}
	
	if (empty($aRes)) {
		printf('<div>No documents matched your query</div>');
		return;
	}
	
	printf('<form action="" method="post" id="submit">');
	foreach ($aRes as $aRecord) {

		$sTime1 = $objDb->TranslateDate($aRecord["added"]);
		$sTime2 = $objDb->TranslateDate($aRecord["dated"], false);

		printf('<table class="item">');
		printf('<tr><td><input onclick="batchMode()" type="checkbox" name="batch[]" value="%d"/> Batch<br/><a href="view.php?id=%d"><img src="thumb.php?id=%d&width=100" alt="thumbnail"/></a></td>', $aRecord["id"], $aRecord["id"], $aRecord["id"]);	
		printf('<td><table class="item-info"><tr>');
		printf('<th>Scanned:</th><td>%s</td></tr>', $sTime1);
		printf('<th>Dated:</th><td>%s</td></tr>', $sTime2);
		printf('<tr><th>Category:</th><td>%s</td></tr>', $aRecord["name"]);
		printf('<tr><th>Pages:</th><td>%s</td></tr>', $aRecord["pages"]);
		printf('<tr><td colspan="2" style="text-align: center">');
		printf('<a href="view.php?id=%d">View</a> ', $aRecord["id"]);
		printf('<a href="download.php?id=%d">Download</a> ', $aRecord["id"]);
		printf('<a href="delete.php?id=%d">Delete</a> ', $aRecord["id"]);
		printf('</td></tr></table></td></tr>');
		printf('</table>');
	}
	printf('</form>');
}

function search($objDb, $sKeywords) {
	$aRes = $objDb->Search($sKeywords);
	
	display_results($aRes, $objDb);
	
	if (!empty($aRes)) {
		printf('<div class="tally">Found %d documents.</div>', count($aRes));
	}
}

function GetMenu() {
	return array("Latest scanned", "Latest dated", "Search", "Category", "Timeline");
}

function render_menu() {
	$aMenu = GetMenu();
	$bFirst = true;
	
	print('<div class="menu">');
	foreach ($aMenu as $iIndex => $sItem) {
		if ($_SESSION["view"] == $iIndex) {
			print($sItem);
		} else {
			printf('<a href="index.php?view=%d">%s</a>', $iIndex, $sItem);
		}
		print(" | ");
	}
	print('<a href="categories.php">Edit categories</a>');
	print(' | <a href="qrpage.php">Splitter Document</a>');
	print('</div>');
}

function render_submenu() {
	print('<div id="submenu" style="display: none" class="menu">');
	printf('<a href="%s">Create category</a>', "javascript:batch('create_category.php')");
	printf(' | <a href="%s">Set category</a>', "javascript:batch('set_category.php')");
	printf(' | <a href="%s">Delete</a>', "javascript:batch('delete.php')");
	print('</div>');
}

function render_search() { 
?>
		<h2>Search for a specific document</h2>
		<form action="index.php" method="get">
			<input style="width: 800px" type="text" name="keywords" value="<?php if (isset($_GET["keywords"])) print(htmlspecialchars($_GET["keywords"])); ?>"/>
			<input type="submit" name="search" value="Search"/>
			<input type="submit" name="clear" value="Clear"/>
		</form>
		<p>
			Hint!<br/>
			Separate several words using space, or enclose them in quotes to search for phrases. Any word, phrase or keyword can be negated (ie, must NOT be contained in result) by placing a minus in front of it.
			Phrases should have the minus within the actual phrase (ie, "-some phrase" will negate while -"some phrase" will not) This will be fixed in the future.
			All searching is case-insensitive
		</p>
		<p>
			Search also supports the use of keywords, special words which allows you to limit the result based on other factors such as dates, categories, etc.
			<ul>
				<li>
					year or scan_year<br/>
					Only display documents for a certain year or years. Years must be written out using 4 digits, 2 digits will be ignored.
					scan_year will use the date you added the document to the system instead of the date of the document.
				</li>
				<li>
					month or scan_month<br/>
					Only display documents for a certain month or months. Uses numerical representation of month, so values 1 to 12 are accepted.
					scan_month will use the date you added the document to the system instead of the date of the document.
				</li>
				<li>
					day or scan_day<br/>
					Only display documents for a certain day or days. Uses numerical representation of day, so values 1 to 31 are accepted.
					scan_day will use the date you added the document to the system instead of the date of the document.
				</li>
				<li>
					category<br/>
					Only display documents marked with a specific category, doesn't have to be the complete category name. Please enclose entire keyword with quotes if the category has spaces in it.
				</li>
			</ul>
			Any numerical keyword accepts ranges, for example:
			<p>
				From 2010 to now = "year:2010-"<br/>
				Up to 2010 = "year:-2010"<br/>
				Between 2009 and 2011  = "year:2009-2011"<br/>
			</p>
		</p>
<?php 
}

function render_category($objDb) {
?>
		<h2>Display all documents in specific category</h2>
		<p>
			Please choose one of the categories below to see all documents tagged with it.
		</p>
<?php
	printf('<form action="index.php" method="get"><select name="category">');
	$aCat = $objDb->GetCategories();
	$iCategory = intval($_GET["category"]);
	foreach ($aCat as $aEntry) {
		printf('<option value="%d" %s>%s</option>',
			$aEntry["id"],
			(isset($_GET["category"]) && $aEntry["id"] == $iCategory) ? "selected=selected" : "",
			htmlspecialchars($aEntry["name"]));
	}				
	printf('</select>');
	printf('<input type="submit" name="" value="List"/></form>');
}

function render_timeline($objDb) {
	$aItems = $objDb->GetTimeline(FALSE, FALSE);
	
	if ($aItems === FALSE || empty($aItems)) {
		return;
	}
	
	// Find the first & last date, as well as the max document count
	$iNewest = 0;
	$iOldest = time();
	$iMaxCount = 0;
	foreach ($aItems as $aItem) {
		if ($aItem["dated"] != 0) {
			if ($aItem["dated"] < $iOldest)
				$iOldest = $aItem["dated"];
			if ($aItem["dated"] > $iNewest)
				$iNewest = $aItem["dated"];
		if ($aItem["entries"] > $iMaxCount)
			$iMaxCount = $aItem["entries"];
		}
	}
	
	// Convert into years
	$iNewest = date("Y", $iNewest)+1;
	$iOldest = date("Y", $iOldest);
	
	// Now we know, time to render
	$a = 1; // Skip undated items
	$empty = 0;
	printf("Start: %s<br/>End: %d<br/>Max count: %d<hr/>", $iNewest, $iOldest, $iMaxCount);
	
	$iLastMonth = -1;
	$sLabels = "";
	for ($y = $iOldest; $y != $iNewest; $y++) {
		printf('<div class="date" style="width: 1px; height: 100px; margin-top: 0px; background-color: black"></div>');
		$sLabels .= sprintf('<div class="datelabel"><a href="">%04d</a></div>', $y);
		for ($m = 0; $m != 12; $m++) {
			//printf("%04d%02d = %s | ", $y, $m+1, date("Ym", $aItems[$a]["dated"]));
			if (isset($aItems[$a]) && sprintf("%04d%02d", $y, $m+1) == date("Ym", $aItems[$a]["dated"])) {
				if ($empty != 0) {
					printf('<div class="date" style="width: %dpx"></div>', 10 * $empty);
					$empty = 0;
				}
				$iAdjusted = (100 * $aItems[$a]["entries"]) / $iMaxCount;
				printf('<div class="date" style="height: %dpx; margin-top: %dpx"></div>', $iAdjusted, 100 - $iAdjusted);
				$a++;
			} else {
				$empty++;
			}
		}
	}	
	if ($empty != 0) {
		printf('<div class="date" style="width: %dpx"></div>', 10 * $empty);
		$empty = 0;
		printf('<div class="date" style="width: 1px; height: 100px; margin-top: 0px; background-color: black"></div>');
	}
	
	printf("<br/>%s\n", $sLabels);
}

	session_start();

	if (isset($_GET["clear"])) 
		header("Location: index.php");

	if (isset($_GET["view"])) {
		$iTotal = count(GetMenu())-1;
		$iNew = intval($_GET["view"]);
		$_SESSION["view"] = min($iTotal, max(0, $iNew));
		header("Location: index.php");
		exit;
	}

	if (!isset($_SESSION["view"])) {
		$_SESSION["view"] = 0;
	}

	$objDb = new ScannerDB();
	$objDb->open();

?>
<html>
	<head>
		<title>lagerDox</title>
		<style type="text/css">
			div.menu {
				border-top: 1px solid; 
				border-bottom: 1px solid; 
				background-color: #eeeeee; 
				padding: 2px; 
				margin-bottom: 20px
			}
			
			div.date {
				width: 10px;
				margin-top: 100px;
				height: 0px;
				background-color: #00ff00;
				color: #00ff00;
				display: inline-block;
			}

			div.datelabel {
				border-top: 1px solid; 
				width: 121px;
				color: #000000;
				display: inline-block;
				text-align: center;
			}
			
			body {
				font-family: Verdana;
				font-size: 10pt;
			}

			table.item-info {
				height: 136px;
				font-size: 8pt;
			}
			
			th {
				text-align: right;
				vertical-align: top;
			}

			td {
				vertical-align: top;
			}
			
			table.item {
				width: 350px;
				height: 180px;
				display: inline-block;
				padding: 5px;
				margin: 2px;
				background-color: #eeeeee;
				border: 1px solid;
				font-size: 8pt;
			}
		</style>
		<script type="text/javascript">
			function batchMode() {
				var form = document.getElementById("submit");
				var checked = 0;
				var total = 0;
				
				for (i = 0; i != form.length; ++i) {
					if (form.elements[i].checked)
						checked++;
					total++;
				}
				
				var submenu = document.getElementById("submenu");
				if (submenu != null) {
					if (checked != 0) {
						submenu.style.display = "";
					} else {
						submenu.style.display = "none";
					}
				}
			}
			
			function batch(sURL) {
				var form = document.getElementById("submit");
				
				form.action = sURL;
				form.submit();
			}
		</script>
	</head>
	<body>
		<h1>Welcome to lagerDox</h1>
		<p>
			This site gives you easy access to all scanned documents. You can search, download, delete and classify the documents as you please.
		</p>
<?php
	render_menu(); 

	switch ($_SESSION["view"]) {
		case 0: // Last 10 scanned
			render_submenu();
			last10($objDb, false);
			break;
		case 1: // Last 10 dated
			render_submenu();
			last10($objDb, true);
			break;
		case 2: // Search
			render_submenu();
			render_search();
			if (isset($_GET["keywords"]) && trim($_GET["keywords"]) != "") {
				search($objDb, $_GET["keywords"]);
			}
			break;
		case 3: // Category
			render_submenu();
			render_category($objDb);
			if (isset($_GET["category"]))
				category($objDb, $_GET["category"]);
			else	
				category($objDb, 0);
			break;
		case 4: // Timeline
			// Show a line with graphs indicating amount of data on a date, normalize it by the most found amount
			render_timeline($objDb);
			break;
	}
?>
	</body>
</html>

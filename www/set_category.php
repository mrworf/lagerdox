<?php
require_once("includes/db.php");

	if (!isset($_POST["batch"])) {
		header("Location: index.php");
		exit;
	}

	$objDb = new ScannerDB();
	$objDb->open();
	
	if (isset($_POST["category"]) || (isset($_POST["action"]) && $_POST["action"] == "deduce")) {
		$bDeduce = (isset($_POST["action"]) && $_POST["action"] == "deduce");
		// Apply changes
		// TODO: Use SQL, not code loop!
		foreach ($_POST["batch"] as $id) {
			if ($bDeduce) {
				$iCat = $objDb->GuessCategoryForDocument($id);
				if ($iCat !== FALSE) {
					$objDb->UpdateDocumentCategory($id, $iCat);
				}
			} else {
				$objDb->UpdateDocumentCategory($id, $_POST["category"]);
			}
		}
		
		// Go back to main
		header("Location: index.php");
		exit;
	}

	// Iterate through the data (this should probably display a progressbar
	// in the browser, since the user can select a gazillion files.
	$aItems = array();
	
	$iCat = FALSE;
	foreach ($_POST["batch"] as $id) {
		$aRes = $objDb->GetDetails($id);
		if ($aRes === FALSE)
			continue;
			
		if ($iCat === FALSE) {
			$iCat = $aRes["category"];
		}
		else if ($iCat != $aRes["category"]) {
			$iCat === FALSE;
			break;
		}
	}
?>
<html>
	<head>
		<title>Set category on multiple documents</title>
		<style type="text/css">
			img {
				margin: 5px;
				border: 1px solid;
			}
			
		</style>
		
		<script type="text/javascript">
			function confirmChange() {
				var r = confirm("WARNING!\n\nThis will change <?php printf("%d document%s", count($_POST["batch"]), count($_POST["batch"]) > 1 ? "s" : ""); ?>, are you sure?\n\nThis change cannot be undone automatically!");
				if (r) {
					document.getElementById("action").value = "change";
					document.getElementById("change").submit();
				}
			}
			
			function confirmDeduce() {
				var r = confirm("WARNING!\n\nThis may change <?php printf("%d document%s", count($_POST["batch"]), count($_POST["batch"]) > 1 ? "s" : ""); ?>, are you sure?\n\nThis change cannot be undone automatically!");
				if (r) {
					document.getElementById("action").value = "deduce";
					document.getElementById("change").submit();
				}
			}
		</script>
	</head>
	<body>
		<a href="index.php">Back to front page</a><hr/>
		<h1>Set category on multiple documents</h1>
		<?php
			printf('<form id="change" action="set_category.php" method="post">');
			foreach ($_POST["batch"] as $id)
				printf('<input type="hidden" name="batch[]" value="%d"/>', $id);
			printf('<input type="hidden" id="action" name="action" value=""/>');
			printf('<select name="category">');

			$aCat = $objDb->GetCategories();
			foreach ($aCat as $aEntry) {
				printf('<option value="%d" %s>%s</option>',
					$aEntry["id"],
					($iCat !== FALSE && $iCat == $aEntry["id"]) ? "selected=selected" : "",
					htmlspecialchars($aEntry["name"]));
			}
			printf('</select>');
			printf('<input type="button" name="update" value="Change" onclick="confirmChange()"/></form>');
			printf('<input type="button" name="deduce" value="Deduce" onclick="confirmDeduce()"/></form>');
		?>
		<hr/>
		<?php
			// We need to visualize the results ... urgh
			foreach ($_POST["batch"] as $id) {
				printf('<a href="view.php?id=%d" target="_new"><img id="doc%d" src="thumb.php?id=%d&width=100" alt="thumbnail"/></a>', $id, $id, $id);
			}
		?>
	</body>
</html>

<?php
require_once("includes/db.php");

	if (!isset($_GET["id"])) {
		header("Location: index.php");
		exit;
	}

	$objDb = new ScannerDB();
	$objDb->open();

	$aRes = $objDb->GetDetails($_GET["id"]);
	if ($aRes === FALSE) {
		header("Location: index.php");
		exit;
	}

	if (isset($_POST["update"]) && isset($_POST["category"])) {
		$objDb->UpdateDocumentCategory($_GET["id"], $_POST["category"]);
		header("Location: view.php?id=" . $_GET["id"]);
		exit;
	}

	if (isset($_GET["autodate"])) {
		$iDate = $objDb->GuessDateForDocument($_GET["id"], $aRes["added"]);
		if ($iDate != 0 && $iDate !== FALSE) {
			$objDb->UpdateDocumentDate($_GET["id"], $iDate);
		}
		header("Location: view.php?id=" . $_GET["id"]);
		exit;
	}

	if (isset($_GET["resetdate"])) {
		$objDb->UpdateDocumentDate($_GET["id"], 0);
		header("Location: view.php?id=" . $_GET["id"]);
		exit;
	}

	if (isset($_GET["autocategory"])) {
		$iCat = $objDb->GuessCategoryForDocument($_GET["id"]);
		if ($iCat !== FALSE) {
			$objDb->UpdateDocumentCategory($_GET["id"], $iCat);
		}
		header("Location: view.php?id=" . $_GET["id"]);
		exit;
	}
	
	if (isset($_GET["debug"]))
		$bDebug = TRUE;
	else
		$bDebug = FALSE;

?>
<html>
	<head>
		<title>Viewing document</title>
		<style type="text/css">
			img {
				margin: 5px;
				border: 1px solid;
			}
		</style>
	</head>
	<body>
		<a href="index.php">Back to front page</a> - <a href="view.php?id=<?php print($_GET["id"]); ?>&debug">Debug</a><hr/>
		<h1>Viewing document</h1>
		<table>
			<tr>
				<th>Scanned:</th>
				<td><?php printf($objDb->TranslateDate($aRes["added"])); ?></td>
			</tr>
			<tr>
				<th>Dated:</th>
				<td>
					<?php printf($objDb->TranslateDate($aRes["dated"], false)); ?>
					<?php if ($aRes["dated"] == 0) printf(' [<a href="view.php?id=%d&autodate">deduce</a>]', $_GET["id"]); ?>
					<?php if ($aRes["dated"] != 0) printf(' [<a href="view.php?id=%d&resetdate">reset</a>]', $_GET["id"]); ?>
				</td>
			</tr>
			<tr>
				<th>Category:</th>
<?php if (isset($_GET["category"])) {
				printf('<td><form action="view.php?id=%d" method="post"><select name="category">', $_GET["id"]);

				$aCat = $objDb->GetCategories();
				foreach ($aCat as $aEntry) {
					printf('<option value="%d" %s>%s</option>',
						$aEntry["id"],
						$aEntry["id"] == $aRes["category"] ? "selected=selected" : "",
						htmlspecialchars($aEntry["name"]));
				}
				printf('</select>');
				printf('<input type="submit" name="update" value="Change"/><input type="button" onclick="history.back();" value="Cancel"/></form>');
				printf('</td>');
      } else { ?>
				<td><?php print($aRes["name"]); ?>
					<?php if ($aRes["category"] == 0) { ?>
						[<a href="view.php?id=<?php print($_GET["id"]); ?>&autocategory">deduce</a>] 
					<?php } ?>
					[<a href="view.php?id=<?php print($_GET["id"]); ?>&category">change</a>] 
					[<a href="create_category.php?id=<?php print($_GET["id"]); ?>">create new</a>]
				</td>
<?php } ?>
			</tr>
			<tr>
				<th>Pages:</th>
				<td><?php print($aRes["pages"]); ?></td>
			</tr>
			<tr>
				<th>Size:</th>
				<td><?php print($objDb->TranslateFilesize(filesize($aRes["filename"]))); ?></td>
			</tr>
			<tr>
				<th>Options:</th>
				<td>
					<?php if ($aRes["pages"] > 1) { ?>
						<a href="split.php?id=<?php print($aRes["id"]); ?>">Split</a>
					<?php } else { ?>
						Split
					<?php } ?>
					<a href="download.php?id=<?php print($aRes["id"]); ?>">Download</a>
					<a href="delete.php?id=<?php print($aRes["id"]); ?>">Delete</a>
				</td>
			</tr>
		</table>
		<h2>Preview...</h2>
<?php
	for ($i = 0; $i < $aRes["pages"]; ++$i) {
		printf('<img src="thumb.php?id=%d&width=300&page=%d" title="%s"/>', $_GET["id"], $i+1, "Page " . $i+1);
	}
	
	if ($bDebug) {
		$objDM = new DataMining();
		
		print("<hr/><h3>Debug information</h3>\n");
		$sText = $objDb->GetRawText($_GET["id"]);
		printf('<pre style="border: 2px inset">%s</pre>', $sText);
		printf('<h4>Date when trying to deduce</h4><br/><pre>');
		print($objDM->GuessOriginalDate($sText, $aRes["added"], TRUE));
		print("</pre>\n");
	}
?>
	</body>
</html>

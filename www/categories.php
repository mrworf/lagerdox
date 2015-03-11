<?php
require_once("includes/db.php");

	$objDb = new ScannerDB();
	$objDb->open();
	
	$aCat = $objDb->GetCategories();

	if (isset($_GET["edit"])) {
		// See if we have it
		$aRecord = false;
		foreach ($aCat as $aEntry) {
			if ($aEntry["id"] == $_GET["edit"]) {
				$aRecord = $aEntry;
				break;
			}
		}

		if ($aRecord === FALSE || $aRecord["id"] == 0) {
			header("Location: categories.php");
			exit;
		}
	}
	
	if (isset($_POST["cmd"])) {
		$id = 0;
		if (isset($_POST["id"]))
			$id = intval($_POST["id"]);
			
		$sName = trim($_POST["name"]);
		$sKeywords = trim($_POST["keywords"]);
		
		if (isset($_POST["disconnect"]) && $_POST["disconnect"] == "yes")
			$bRemoveLink = true;
		else
			$bRemoveLink = false;
		
		switch (strtolower($_POST["cmd"])) {
			case "delete":
				if ($id != 0) {
					$objDb->DeleteCategory($id);
				}
				break;
			case "save":
				if ($sName != "" && $id != 0) {
					$objDb->UpdateCategory($id, $sName, $sKeywords, $bRemoveLink);
				}
				break;
			case "add":
				if ($sName != "") {
					$objDb->AddCategory($sName, $sKeywords);
				}
				break;
		}
		header("Location: categories.php");
		exit;
	}

?>
<html>
	<head>
		<title>Edit categories</title>
		<style type="text/css">
		</style>
	</head>
	<body>
		<a href="index.php">Back to front page</a><hr/>
		<h1>Edit categories</h1>
<?php if (!isset($_GET["edit"])) { ?>
		<table>
			<tr>
				<th>Name</th>
				<th>Usage</th>
				<th>Keywords (for automatic categorization)</th>
				<th>Options</th>
			</tr>
<?php
	foreach ($aCat as $aEntry) {
		printf('<tr><td><a href="index.php?category=%d">%s</a></td><td>%d</td><td>%s</td><td>',
			$aEntry["id"],
			$aEntry["name"],
			$aEntry["inuse"],
			$aEntry["keywords"]);
			
		if ($aEntry["id"] != 0) {
			printf('<a href="categories.php?edit=%d">Edit</a></td></tr>' . "\n",
				$aEntry["id"]);
		}
	}
?>
		</table>

		<h2>Add new category</h2>
		<form action="categories.php" method="post">
			<table>
				<tr>
					<th>Name</th>
					<td>
						<input type="text" name="name" value=""/>
					</td>
				</tr>
				<tr>
					<th>Keywords</th>
					<td>
						<input type="text" name="keywords" value=""/>
					</td>
				</tr>
				<tr>
					<td colspan="2">
						<input type="submit" name="cmd" value="Add"/>
					</td>
				</tr>
			</table>
		</form>


<?php } else if ($aRecord["id"] > 0) { ?>
		<form action="categories.php" method="post">
			<input type="hidden" name="id" value="<?php print($aRecord["id"]); ?>"/>
			<table>
				<tr>
					<th>Name</th>
					<td>
						<input type="text" name="name" value="<?php print(htmlspecialchars($aRecord["name"])); ?>"/>
					</td>
				</tr>
				<tr>
					<th>Keywords</th>
					<td>
						<input type="text" name="keywords" value="<?php print(htmlspecialchars($aRecord["keywords"])); ?>"/>
					</td>
				</tr>
				<tr>
					<td colspan="2"><input type="checkbox" name="disconnect" value="yes"/> Remove category from documents when altering this category</td>
				</tr>
				<tr>
					<td colspan="2">
						<input type="submit" name="cmd" value="Save"/>
						<input type="submit" name="cmd" value="Delete"/>
						<input type="submit" name="cmd" value="Cancel"/>
					</td>
				</tr>
			</table>
		</form>
<?php } ?>
	</body>
</html>

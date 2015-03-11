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
	
	if (isset($_GET["yes"]) && $_GET["yes"] == "indeed") {
		$objDb->Delete($_GET["id"]);
		header("Location: index.php");
		exit;
	}

?>
<html>
	<head>
		<title>Delete document</title>
		<style type="text/css">
			img {
				margin: 5px;
				border: 1px solid;
			}
			
			h2 {
				display: inline;
			}
		</style>
	</head>
	<body>
		<a href="index.php">Back to front page</a><hr/>
		<h1>Delete document</h1>
		<img src="thumb.php?id=<?php print($_GET["id"]); ?>&width=300&page=1" title="Page 1" align="left"/>
		<table>
			<tr>
				<th>Scanned:</th>
				<td><?php printf($objDb->TranslateDate($aRes["added"])); ?></td>
			</tr>
			<tr>
				<th>Category:</th>
				<td><?php print($aRes["name"]); ?></td>
			</tr>
			<tr>
				<th>Pages:</th>
				<td><?php print($aRes["pages"]); ?></td>
			</tr>
			<tr>
				<th>Options:</th>
				<td>
					<a href="view.php?id=<?php print($aRes["id"]); ?>">View</a>
					<a href="download.php?id=<?php print($aRes["id"]); ?>">Download</a>
				</td>
			</tr>
		</table>
		<br/>
		<h2>Sure you want to delete this? </h2>(this cannot be undone!)
		<br/>
		<br/>
		<a href="delete.php?id=<?php print($_GET["id"]); ?>&yes=indeed">Yes, I am totally sure of this</a>
	</body>
</html>

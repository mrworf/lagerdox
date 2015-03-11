<?php
require_once("includes/db.php");
require_once("includes/processing.php");

	if (isset($_GET["id"])) {
		// Convert!
		$id = $_GET["id"];
	} else {
		header("Location: index.php");
		exit;
	}

	$objDb = new ScannerDB();
	$objDb->open();

	$aRes = $objDb->GetDetails($id);
	if ($aRes === FALSE) {
		header("Location: index.php");
		exit;
	}

	$iSplit = 0;	
	if (isset($_POST["split"])) {
		$iSplit = intval($_POST["split"]);
		if ($iSplit < 1 || $iSplit > ($aRes["pages"]-1) || $aRes["pages"] < 2) {
			// Really want to split this one don't you? But it's not possible
			header("Location: index.php");
			exit;
		}
		
		// Okay! This should work, now, generate some kind of UI while we do it since it takes time
		// to do that, we need to disable all kind of buffering...
		@apache_setenv('no-gzip', 1);
		@ini_set('zlib.output_compression', 0);
		@ini_set('implicit_flush', 1);
		for ($i = 0; $i < ob_get_level(); $i++) { ob_end_flush(); }
		ob_implicit_flush(1);
	}
?>
<html>
	<head>
		<title>Split document into multiple documents</title>
		<style type="text/css">
			img {
				margin: 5px;
				border: 1px solid;
			}
		</style>
	</head>
	<body>
<?php if ($iSplit != 0) { ?>
		<h1>Split document into multiple documents</h1>
		Please wait, working...
		<pre>
<?php 
		// This is complicated, essentially we rescan the document and then afterwards we delete the original

		$iErr = 0;
		if (($iErr = InitializeWork()) == 0) {
			if (($iErr = ProcessFile($aRes["filename"], $iSplit)) != 0) {
				printf("ProcessFile() failed with %d\n", $iErr);
			} else {
				// Success! Remove original document
				$objDb->Delete($id);
			}
			if (($iErr = CleanupWork()) != 0) {
				printf("CleanupWork() failed with %d\n", $iErr);
			}
		} else
			printf("InitializeWork() failed with %d\n", $iErr);
?>
		</pre>
		<a href="index.php">Done</a>
<?php } else { ?>
		<a href="index.php">Back to front page</a><hr/>
		<h1>Split document into multiple documents</h1>
		<table>
			<tr>
				<th>Scanned:</th>
				<td><?php printf($objDb->TranslateDate($aRes["added"])); ?></td>
			</tr>
			<tr>
				<th>Dated:</th>
				<td>
					<?php printf($objDb->TranslateDate($aRes["dated"], false)); ?>
				</td>
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
				<th>Size:</th>
				<td><?php print($objDb->TranslateFilesize(filesize($aRes["filename"]))); ?></td>
			</tr>
		</table>
		<br/>
<?php
		if ($aRes["pages"] < 2) {
			// Just in case user inputted the URL manually
			printf("This document can not be split since there isn't enough pages");
		} else {
			printf('<form action="split.php?id=%d" method="post">Split document after every <select name="split">', $id);
			printf('<option value="1">page</option>');
			for ($i = 1; $i < ($aRes["pages"]-1); $i++) {
				printf('<option value="%d">%d page%s</option>', $i+1, $i+1, $i > 0 ? "s" : "");
			}
			printf('</select>');
			printf('<input type="submit" name="go" value="Go"/>');
			printf('</form>');
		}
?>
		<h2>Preview...</h2>(TODO: Should show result of split using javascript)<br/>
<?php
	for ($i = 0; $i < $aRes["pages"]; ++$i) {
		printf('<img src="thumb.php?id=%d&width=300&page=%d" title="%s"/>', $_GET["id"], $i+1, "Page " . $i+1);
	}
?>
<?php } ?>
	</body>
</html>

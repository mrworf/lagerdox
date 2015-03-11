<?php
	header("Content-Type: application/octet-stream");

	// PHP will STILL buffer output if you use sessions... WTF!
	@apache_setenv('no-gzip', 1);
	@ini_set('zlib.output_compression', 0);
	@ini_set('implicit_flush', 1);
	for ($i = 0; $i < ob_get_level(); $i++) { ob_end_flush(); }
	ob_implicit_flush(1);

	if (!isset($_GET["pipe"]))
		exit;
	else
		$sPipe = $_GET["pipe"];

	$fp = fopen($sPipe, "r");
	if ($fp !== FALSE) {
		do {
			$sData = fgets($fp);
			printf("%s", $sData);
			flush();
		} while (!feof($fp));
		fclose($fp);
	}
	// Not ideal, command must delete the pipe when done
	unlink($sPipe);
	exit;

<?php
require_once("includes/db.php");
require_once("includes/processing.php");

function parseUpload($sPipe)
{
	if (!isset($_FILES["document"])) {
		print("ERROR: No files attached!");
		return;
	}

	$aFiles = $_FILES["document"];
	$iL = count($aFiles["tmp_name"]);

	print_r($aFiles);

	for ($iC = 0; $iC != $iL; ++$iC) {
		if ($aFiles["error"][$iC] == 0) {
			// TODO: Add all files to process to a textfile so we can queue up the work as it were
			// First, move the file into safety
			if (move_uploaded_file($aFiles["tmp_name"][$iC], "/tmp/" . $aFiles["name"][$iC])) {
				$sCmd = sprintf('%s "%s" %s >/dev/null &', 
			        	        "/mnt/storage/content/Scanner/scripts/upload.sh",
			                	"/tmp/" . $aFiles["name"][$iC],
				                $sPipe
				                );
				exec($sCmd);
			} else {
				printf("Unable to move file %s to %s\n", $aFiles["tmp_name"][$iC], "/tmp/" . $aFiles["name"][$iC]);
			}
			return;
		} else {
			printf("File \"%s\" failed with error %d\n", $aFiles["error"][$iC]);
		}
	}
}

	// Make use of https://github.com/valums/file-uploader in the future
	session_start();

	if (isset($_SESSION["pipe"]) && $_SESSION["pipe"]["action"] != "upload") {
			unset($_SESSION["pipe"]);
	}
	if (!isset($_SESSION["pipe"])) {
		$_SESSION["pipe"] = array("action" => "upload", "fifo" => tempnam(sys_get_temp_dir(), time()));
	}

	$bUpload = FALSE;
	$sPipe = $_SESSION["pipe"]["fifo"];

	if (isset($_FILES) && isset($_FILES["document"])) {
		header("Content-Type: text/plain");
		$bUpload = TRUE;
		posix_mkfifo($sPipe, 0644);
		
		parseUpload($sPipe);
		exit;
	}

?>
<html>
	<head>
		<title>Upload document</title>
		<style type="text/css">
			img {
				margin: 5px;
				border: 1px solid;
			}
		</style>
		<script type="text/javascript">
				function checkUpload() {
					obj = document.getElementById("filename");
					if (obj == null) {
						alert("Page is broken, please reload");
						return false;
					}
						
					if (obj.value == "") {
						alert("Please select a file before pressing upload");
						return false;
					}
					
//					parent.document.getElementById("uploadframe").style.display = "none";
					parent.document.getElementById("info").style.display = "";
					parent.InitiateLog();
					return true;	
				}
				
				var xmlHttp = null;
				var pollTimer = null;
				var workTimer = null;
				
				function InitiateLog() {
					var Url = "logging.php?pipe=<?php print($sPipe); ?>";
					
					xmlHttp = new XMLHttpRequest();
					xmlHttp.onreadystatechange = ProcessLog;
					xmlHttp.open("GET", Url, true);
					xmlHttp.send(null);
					
					if (pollTimer == null)
						pollTimer = window.setInterval(ProcessLog, 1000);
					if (workTimer == null)
						workTimer = window.setInterval(Animate, 200);
				}
				
				function Animate() {
					var str = document.getElementById("working").innerHTML;
					
					if (str == "...")
						str = "";
					else
						str += ".";
						
					document.getElementById("working").innerHTML = str;
				}
				
				function StopAnimation() {
					workTimer = clearInterval(workTimer);
					document.getElementById("working").innerHTML = "...Done!";
				}
				
				function ProcessLog() {
					var obj = document.getElementById("progress");
					
					document.getElementById("state").innerHTML = xmlHttp.readyState;
					document.getElementById("status").innerHTML = xmlHttp.status;
					

					if (xmlHttp.responseText === null)
						return;

					obj.innerHTML = xmlHttp.responseText.replace(/\n/g, "<br/>");

					// We are DONE!
					if (xmlHttp.readyState == 4) {
						pollTimer = clearInterval(pollTimer);
						inProgress = false;
						
						// However, if length is zero, we rerequest
						if (xmlHttp.responseText.length == 0) {
							setTimeout("InitiateLog();", 100);
						} else
							StopAnimation();
					}
				}
		</script>
	</head>
	<body>
		<?php if (isset($_GET["subframe"])) { ?>
			<form onSubmit="return checkUpload();" action="upload.php" method="post" enctype="multipart/form-data">
				<div id="upload">Please select file to upload: <input id="filename" multiple="true" type="file" name="document[]" accept="application/pdf"/> <input  type="submit" name="upload" value="Upload" /></div>
				<div id="info" style="display: none">File is being uploaded, please wait.</div>
			</form>
		<?php } else { ?>
			<a href="index.php">Back to front page</a>
			<h1>Upload document</h1>
			<hr/>
			
			<iframe style="width: 100%" id="uploadframe" src="upload.php?subframe"></iframe>
			<div id="info" style="display: none">
				<h2>Processing upload</h2>
				Processing, please wait<span id="working"></span>
				<div id="debug" style="display: ">
					xmlHttp.readystate = <span id="state"></span><br/>
					xmlHttp.status = <span id="status"></span><br/>
				</div>
				<div id="progress" style="font-family: Courier">
				</div>
			</div>
		<?php } ?>
	</body>
</html>

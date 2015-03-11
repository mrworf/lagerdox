<?php
	session_start();
	$_SESSION["test"] = "Hello";
?>
<html>
	<head>
		<title>Upload test</title>
		<script type="text/javascript">
			function createRequestObject() {
				var http;
				if (navigator.appName == "Microsoft Internet Explorer") {
					http = new ActiveXObject("Microsoft.XMLHTTP");
				} else {
					http = new XMLHttpRequest();
				}
				return http;
			}
			
			function sendRequest() {
				var http = createRequestObject();
				var date = new Date();
				http.open("GET", "progress.php?ts=" + date.getTime());
				http.onreadystatechange = function () { handleResponse(http); };
				http.send(null);
			}
			
			function handleResponse(http) {
				var response;
				var org;
				
				if (http.readyState == 4) {
					org = http.responseText;
					response = org.split("|");

					if (response.length > 1) {
						for (var i = 1; i != response.length; ++i) {
							document.getElementById("file" + (response[i]-1)).className = "file-done";
						}
					}

					if (response[0] < 100) {
						if (response[0] > 0)
							document.getElementById("progressdone").style.width = response[0] + "%";
						setTimeout("sendRequest()", 1000);
					} 
				}
			}


			function historyFiles() {
				var txt = document.getElementById("history");
				var files = document.getElementById("files").files;
				var content = '';
				
				for (var i = 0; i != files.length; ++i) {
					content += files[i].name + '<br/>';
				}
				txt.innerHTML += content;
			}

			function showFiles() {
				var txt = document.getElementById("pending");
				var files = document.getElementById("files").files;
				var content = '';
				
				for (var i = 0; i != files.length; ++i) {
					content += '<div class="file-pending" id="file' + i + '"></div><span id="name' + i + '">' + files[i].name + '</span><br/>';
				}
				txt.innerHTML = content;
				
				if (files.length != 0) {
					document.getElementById("submit").disabled = false;
				}
			}
			
			function showBrowser() {
				document.getElementById("files").click();
			}
			
			function handleUpload() {
				document.getElementById("select").disabled = true;
				document.getElementById("submit").disabled = true;
				document.getElementById("clear").disabled = true;

				document.getElementById("progressdone").style.width = "1%";
				document.getElementById("progressdone").style.display = "block";
				
				setTimeout("sendRequest()", 1000);
			}
			
			function onDone() {
				document.getElementById("progressdone").style.width = "100%";
				
				// Move files into history view
				historyFiles();
				
				resetForm();
			}
			
			function resetForm() {
				// Clear selected files
				var btn = document.getElementById("reset");
				btn.innerHTML = btn.innerHTML;
				document.getElementById("pending").innerHTML = "";

				document.getElementById("select").disabled = false;
				document.getElementById("submit").disabled = true;
				document.getElementById("clear").disabled = false;
				document.getElementById("progressdone").style.display = "none";
			}
		</script>
		
		<style type="text/css">
			.file-pending, .file-done, .file-error {
				width: 12pt;
				height: 12pt;
				border: 1px solid black;
				display: inline-block;
				vertical-align: middle;
				margin-right: 5px;
				margin-top: 1px;
				margin-bottom: 1px;
				margin-left: 1px;
			}
			
			.file-done {
				background-color: green;
			}
			
			.file-error {
				background-color: red;
			}
			
			#progressbar {
				width: 100%;
				height: 12pt;
				border: 1px solid black;
				display: inline-block;
				z-index: auto;
			}

			#progressdone {
				height: 100%;
				width: 10%;
				background-color: aqua;
				display: inline-block;
				border: 1px solid black;
				z-index: auto;
				position: relative;
				left: -1px;
				top: -1px;
				display: none;
			}
			
			.hide {
				display: none;
			}
			
			#pending, #history {
				border: 2px inset;
			}
			
		</style>
	</head>
	<body>
		<h1>Testing upload</h1>
		
		<form action="upload.php" method="POST" id="myForm" enctype="multipart/form-data" target="hidden_iframe" onsubmit="handleUpload()">
			<input type="hidden" value="upload" name="<?php echo ini_get("session.upload_progress.name"); ?>" />
			<span id="reset"><input type="file" id="files" name="userfile" multiple="multiple" onchange="showFiles()" class="hide" /></span>
			<input type="button" id="select" value="Select files..." onclick="showBrowser()"/>
			<input type="button" id="clear" value="Reset" onclick="resetForm()" />
			<input type="submit" id="submit" value="Start Upload" disabled=disabled />
			<div id="progress">
				<div id="progressbar"><div id="progressdone"></div></div><br/>
				Pending<div id="pending"></div>
				History<div id="history"></div>
			</div>
		</form>
		<iframe class="hide" name="hidden_iframe" src="about:blank"></iframe>
		<div id="debug"></div>
	</body>
</html>

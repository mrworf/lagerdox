<?php
	session_start();
	
	if ($_SERVER["REQUEST_METHOD"] !== "POST") {
		exit;
	}
?>
<html>
	<body>
		<script type="text/javascript">
			parent.onDone();
		</script>
	</body>
</html>
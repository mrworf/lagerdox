<?php

/**
 * Contains neato code to generate overlays with a larger image ... I hope
 */

function insert_OverlayHook($id) {
	printf(' onmouseover="showBigThumb(%d)" onmouseout="hideBigThumb()" ', $id);
}

function insert_OverlayJS() {
?>
function showBigThumb(id) {
	
}
<?php

}
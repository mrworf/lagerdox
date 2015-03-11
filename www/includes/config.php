<?php

/**
 * Configuration, make sure to match your system
 */

class Config {
	private static $mConfig = array(
		# Special splitter marker which is used by the processing
		# to indicate where a new page starts in the rawtext.
		"page_splitter" => "_###___NewPage___###_",

		# Language for Tesseract, add more by adding a plus sign.
		# For example, to add swedish, it will be "eng+swe"
		#
		# Don't forget to install the additional languages if you
		# alter this config setting.
		"language" => "eng",

		# Paths for temporary storage and permanent storage
		"path" => array(
			# Folder for temporary work, this will be created
			"tmp"	=> "/tmp/lagerdox/",
			# Where to store processed PDFs
			"dest"	=> "/tmp/"
		),

		# Where to find the tools we need
		"tool" => array(
			"ocr"		=> "/usr/bin/tesseract",
			"convert"	=> "/usr/bin/convert",
			"pdftk"		=> "/usr/bin/pdftk",
			"zbar"		=> "/usr/bin/zbarimg"
		),

		# Permissions to use during storage
		"permission" => array(
			"user"		=> "lagerdox",
			"group"		=> "lagerdox",
			"dirmask"	=> 0775,
			"filemask"	=> 0664
		),

		# MySQL settings
		"database" => array(
			"host"		=> "localhost",
			"username"	=> "lagerdox",
			"password"	=> "password",
			"database"	=> "lagerdox",
		),
	);

	###
	### Helper functions to easily access config data
	###
	public static function GetLanguage() {
		return self::$mConfig["language"];
	}

	public static function GetSplitter() {
		return self::$mConfig["page_splitter"];
	}

	public static function GetPath($key) {
		return self::$mConfig["path"][$key];
	}

	public static function GetTool($key) {
		return self::$mConfig["tool"][$key];
	}

	public static function GetPermission($key) {
		return self::$mConfig["permission"][$key];
	}

	public static function GetDB($key) {
		return self::$mConfig["database"][$key];
	}

	public static function SetPath($key, $value) {
		self::$mConfig["path"][$key] = $value ."/";
	}

	public static function PrintDebug() {
		print_r(self::$mConfig);
	}
}

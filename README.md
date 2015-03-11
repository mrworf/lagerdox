# lagerdox
A document archiver, analyzes pdfs, categories, dates. Allows easy searching of document storage.

Initially never intended for public consumption, so the code quality is somewhat lacking.
But given how many people who've asked me about this during the years, I figured I'd
put it up there for the rest of the world to use.

Have fun! (and feel free to improve it)

# Installation
This is a very quick-n-dirty description of getting this system up and running.
Hopefully all the steps are here, if not, let me know.

## Prerequisits
- `apt-get install tesseract-ocr` 
  Tesseract Optical Character Recognition, the brains of the system
- `apt-get install zbar-tools` QR code detection
  Allows us to detect the splitter page
- `apt-get install imagemagick` Image manipulation 
  Needed to prepare the PDFs for tesseract
- `apt-get install pdftk`
  PDF toolkit, is able to split/merge PDFs
- `apt-get install mysql-server`
  Storage of all data
- `apt-get install apache2`
  Runs the website
- `apt-get install php5`
  Allows the logic to run, ties into apache2 if installed in this order
- `apt-get install php5-mysql`
  Enables use of MySQL from PHP5
- `apt-get install inotify-tools`
  Allows the monitor.sh script to detect folder changes

## Configuration
Create a new database in MySQL, for example, "lagerdox" and make sure to add
a new user who can access it. For example:
`mysql -u root -p`, 
`create database lagerdox;`
`grant all on lagerdox.* to lagerdox@localhost identified by "password";`

Next, import the file `create_database.sql` into the new database you created
in MySQL. For example:
`mysql -u lagerdox -p lagerdox < setup/create_database.sql`

To make things smoother, a new user and group is preferable, for example:
`addgroup lagerdox` and `adduser --system --ingroup lagerdox lagerdox`

This also means that the apache user must have access to the group, like so:
`usermod -a -G lagerdox www-data`

You'll need to edit both `www/includes/config.php` and the `scripts/monitor.sh`
since the first one points out database access and other things (most paths
should be correct if you're using Ubuntu 14.04 or later) and the later script
needs to know where to look for incoming data.

The www folder can easily be symlinked into wherever you want it, I run it as
the /var/www/html folder on my setup to keep it simple. The easiest way of
accomplishing this is by moving html out of the way and symlink the www folder
into it's place (so /var/www/html points to .../lagerdox/www ).

Try browsing to your new website, if everything seems OK (try creating a dummy
catgeory to see read/write access), then you're ready to start using the system.
Should the page come up blank, you most likely forgot to restart apache2 after
adding the mysql module to PHP.

Unfortunately, there is no init script yet for the monitor.sh script, so you'll
need to run that manually for now (I use screen to make that happen). There is
no good reason why it couldn't be run from a init script, so feel free to
improve it.

Anyway, to get the monitor started, just issue:
`sudo -u lagerdox scripts/monitor.sh`, it's sudo because the rights might be
messed up otherwise.

If monitor.sh fails, it's usually due to permission issues, remember that the
user must have write permissions in the directory which holds incoming
documents, or it will not be able to move pdfs out of that folder.

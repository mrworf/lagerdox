import argparse
import ConfigParser
import re
import os
import logging
import sys

class Config:
  def __init__(self):
    parser = argparse.ArgumentParser(description="lagerDox - Your personal storage of documents", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--logfile', metavar="FILE", help="Log to file instead of stdout")
    parser.add_argument('--port', default=7000, type=int, help="Port to listen on")
    parser.add_argument('--listen', metavar="ADDRESS", default="0.0.0.0", help="Address to listen on")
    parser.add_argument('--database', metavar='DATABASE', help='Which database to use')
    parser.add_argument('--dbserver', metavar="SERVER", help='Server running mySQL or MariaDB', dest='host')
    parser.add_argument('--dbuser', metavar='USER', help='Username for server access', dest='username')
    parser.add_argument('--dbpassword', metavar='PASSWORD', help='Password for server access', dest='password')
    parser.add_argument('--setup', action='store_true', default=False, help="Create necessary tables")
    parser.add_argument('--force', action='store_true', default=False, help="Causes setup to delete tables if necessary (NOTE! YOU'LL LOSE ALL EXISTING DATA)")
    parser.add_argument('config', help='Configuration file for lagerDox')
    self.cmdline = vars(parser.parse_args())

    config = ConfigParser.ConfigParser()
    config.add_section("paths")
    config.set("paths", "upload", None)
    config.set("paths", "complete", None)
    config.set("paths", "thumbnails", None)
    config.set('paths', 'html', None)

    config.add_section('database')
    config.set('database', 'host', 'localhost')
    config.set('database', 'username', '')
    config.set('database', 'password', '')
    config.set('database', 'database', 'lagerdox')

    config.add_section('limits')
    config.set('limits', 'file size', 64*1024*1024)
    config.set('limits', 'jobs', 4)
    config.set('limits', 'extensions', "pdf")

    config.add_section('general')
    config.set('general', 'listen', '0.0.0.0')
    config.set('general', 'port', 7000)
    config.set('general', 'logfile', None)

    config.add_section('helpers')
    config.set('helpers', 'convert', 'convert')
    config.set('helpers', 'identify', 'identify')
    config.set('helpers', 'tesseract', 'tesseract')
    config.set('helpers', 'zbarimg', 'zbarimg')
    config.set('helpers', 'pdftk', 'pdftk')

    if not os.path.exists(self.cmdline['config']):
      logging.error('Cannot open configuration file "%s"' % self.cmdline['config'])
      sys.exit(255)

    config.read(self.cmdline['config'])
    self.config = config

  def get(self, section, key):
    if key in self.cmdline:
      return self.cmdline[key]
    else:
      # Handle special cases first!
      if section == 'limits' and key == 'extensions':
        value = self.config.get(section, key).split('^\s+|\s*,\s*|\s+$')
      else:
        value = self.config.get(section, key)
        if section == 'paths':
          # Make it absolute!
          value = os.path.abspath(value)
      # A way of making sure integers are returned as integers
      try:
        return int(value)
      except:
        return value

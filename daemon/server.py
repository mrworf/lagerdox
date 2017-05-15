#!/usr/bin/env python
#
# This file is part of lagerDox.
#
# lagerDox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# lagerDox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with lagerDox.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import argparse
import uuid
import os
import sys

import Storage
import document

""" Parse command line """
parser = argparse.ArgumentParser(description="lagerDox - Your personal storage of documents", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--logfile', metavar="FILE", help="Log to file instead of stdout")
parser.add_argument('--port', default=7000, type=int, help="Port to listen on")
parser.add_argument('--listen', metavar="ADDRESS", default="0.0.0.0", help="Address to listen on")
parser.add_argument('--database', metavar='DATABASE', help='Which database to use')
parser.add_argument('--dbserver', metavar="SERVER", help='Server running mySQL or MariaDB')
parser.add_argument('--dbuser', metavar='USER', help='Username for server access')
parser.add_argument('--dbpassword', metavar='PASSWORD', help='Password for server access')
parser.add_argument('--setup', action='store_true', default=False, help="Create necessary tables")
parser.add_argument('--force', action='store_true', default=False, help="Causes setup to delete tables if necessary (NOTE! YOU'LL LOSE ALL EXISTING DATA)")
cmdline = parser.parse_args()

""" Setup logging first """
logging.getLogger('').handlers = []
logging.basicConfig(filename=cmdline.logfile, level=logging.DEBUG, format='%(asctime)s - %(filename)s@%(lineno)d - %(levelname)s - %(message)s')

""" Continue with the rest """
from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import Application, FallbackHandler
from tornado.websocket import WebSocketHandler

from flask import Flask, jsonify, Response, request, redirect, url_for
from werkzeug.utils import secure_filename
import threading
import Queue
import time

try:
  from flask.ext.cors import CORS # The typical way to import flask-cors
except ImportError:
  # Path hack allows examples to be run without installation.
  import os
  parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  os.sys.path.insert(0, parentdir)
  from flask.ext.cors import CORS

""" Disable some logging by-default """
logging.getLogger("Flask-Cors").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

""" Initiate database connection """
database = Storage.MariaDB()
if not database.connect(cmdline.dbuser, cmdline.dbpassword, cmdline.dbserver, cmdline.database):
  sys.exit(1)

if cmdline.setup:
  if database.setup(cmdline.force):
    logging.info('Tables created successfully')
    database.prepare()
    sys.exit(0)
  else:
    logging.error('Setup failed')
    sys.exit(1)

result = database.validate()
if result == Storage.VALIDATION_NOT_SETUP:
  logging.error('Database is not setup, use --setup to create necessary tables')
  sys.exit(2)
elif result != Storage.VALIDATION_OK:
  logging.error('Internal database error ' + repr(result))
  sys.exit(1)

database.prepare()
#"""
a = document.Analyzer()
a.beginDate()

i = database.query_pages(12)
while True:
  data = i.next()
  if data is None:
    break
  data = data['content']
  a.updateDate(data)
i = a.finishDate()

sys.exit(0)
#"""

""" Initialize the REST server """
app = Flask(__name__)
cors = CORS(app) # Needed to make us CORS compatible

UPLOAD_FOLDER = '/tmp/lagerDox/'
ALLOWED_EXTENSIONS = set(['pdf'])

processList = {}
feeder = document.Feeder(database, UPLOAD_FOLDER)

#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024 # 64MB!

def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handleResult(uid, content):
  logging.debug('%s finished with: %s' % (uid, repr(content)))
  for doc in content:
    feeder.add(uid, doc)

@app.route("/upload", methods=['POST'])
def documentUpload():
  ret = {}

  # check if the post request has the file part
  if 'file' not in request.files:
    ret['error'] = 'No file provided'
  else:
    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
      ret['error'] = 'No file selected'
    elif not allowed_file(file.filename):
      ret['error'] = 'File not allowed'
    else:
      uid = str(uuid.uuid4())
      filename = secure_filename(file.filename)
      path = os.path.join(UPLOAD_FOLDER, uid)
      if not os.path.exists(path):
        os.makedirs(path)
      absfile = os.path.join(UPLOAD_FOLDER, uid, filename)
      file.save(absfile)
      ret['result'] = 'OK'
      ret['uid'] = uid
      logging.info('New file received and stored in "%s"' % absfile)
      processList[uid] = document.Processor(uid, absfile, handleResult)

  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res


""" Finally, launch! """
if __name__ == "__main__":
  app.debug = False
  logging.info("lagerDox running on port %d" % cmdline.port)
  container = WSGIContainer(app)
  server = Application([
    #(r'/events/(.*)', WebSocket),
    (r'.*', FallbackHandler, dict(fallback=container))
    ])
  server.listen(cmdline.port)
  IOLoop.instance().start()

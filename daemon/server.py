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
import shlex

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

from flask import Flask, jsonify, Response, request, redirect, url_for, send_file, abort
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
"""
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
"""

""" Initialize the REST server """
app = Flask(__name__)
cors = CORS(app) # Needed to make us CORS compatible

UPLOAD_FOLDER = '/tmp/lagerDox/'
COMPLETE_FOLDER = '/tmp/lagerDox/done/'
THUMB_FOLDER = '/tmp/lagerDox/thumbs/'
ALLOWED_EXTENSIONS = set(['pdf'])

processList = {}
feeder = document.Feeder(database, UPLOAD_FOLDER, COMPLETE_FOLDER, THUMB_FOLDER)
processor = document.Processor(4)

#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024 # 64MB!

def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handleResult(uid, content):
  logging.debug('%s finished with: %s' % (uid, repr(content)))
  for doc in content:
    feeder.add(uid, doc, processList[uid]['mode'], processList[uid]['extras'])
  del processList[uid]

def deleteDocument(filename):
  thumbfolder = os.path.join(COMPLETE_FOLDER, filename) + '/'
  document = os.path.join(COMPLETE_FOLDER, filename)
  if os.path.exists(thumbfolder):
    shutil.rmtree(thumbfolder)
  if os.path.exists(document):
    os.remove(document)
  return True

def generateThumbs(id):
  id = int(id)
  doc = database.query_document(id)
  pages = database.query_pages(id)
  if doc is None or pages is None:
    logging.error('Cannot create thumbs for non-existant document (%d)' % id)
    return

  meta = {'pages' : [], 'filename' : doc['filename']}
  for page in pages:
    meta['pages'].append(page)

  uid = str(uuid.uuid4())
  path = os.path.join(UPLOAD_FOLDER, uid)
  absfile = os.path.join(COMPLETE_FOLDER, doc['filename'])
  if not os.path.exists(path):
    os.makedirs(path)
  logging.info('Generating thumbnails for "%s"' % absfile)
  processList[uid] = {'process' : document.Process(uid, absfile, path, handleResult, meta), 'mode' : 'thumb', 'extras' : None}
  processor.add(processList[uid]['process'].run)

@app.route("/upload", methods=['POST'], defaults={'mode' : None})
@app.route("/upload/<mode>", methods=['POST'])
def documentUpload(mode):
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
      processList[uid] = {'process' : document.Process(uid, absfile, os.path.dirname(absfile), handleResult), 'mode' : mode, 'extras' : request.args}
      processor.add(processList[uid]['process'].run)

  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route("/status", methods=['GET'])
def getStatus():
  ret = {'jobs' : {} }
  for p in processList:
    ret['jobs'][p] = processList[p]['process'].getState()
  res = jsonify(ret)
  res.status_code = 200
  return res

@app.route("/document/<id>/category/<category>", methods=['PUT'])
@app.route("/document/<id>/category", methods=['DELETE'], defaults={'category' : 0})
def documentCategory(id, category):
  ret = {}
  if request.method == 'PUT' and category != 0:
    if database.assign_category(int(id), int(category)):
      ret['result'] = category
    else:
      ret['error'] = 'Cannot set category'
  elif request.method == 'DELETE':
    if database.assign_category(int(id), 0):
      ret['result'] = category
    else:
      ret['error'] = 'Cannot delete category'
  else:
    ret['error'] = 'Invalid operation'
  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route("/document/<id>/tag/<tag>", methods=['PUT','DELETE'])
@app.route("/document/<id>/tag", methods=['DELETE'], defaults={'tag':0})
def documentTag(id, tag):
  ret = {}
  if request.method == 'PUT':
    if database.assign_tag(int(id), int(tag)):
      ret['result'] = int(tag)
    else:
      ret['error'] = 'Cannot set tag'
  elif request.method == 'DELETE':
    if request.path.endswith('/tag'):
      if database.clear_tag(int(id)):
        ret['result'] = int(id)
      else:
        ret['error'] = 'Cannot clear tags'
    else:
      if database.remove_tag(int(id), int(tag)):
        ret['result'] = int(tag)
      else:
        ret['error'] = 'Cannot delete tag'
  else:
    ret['error'] = 'Invalid operation'
  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route("/document/<id>", methods=['GET','DELETE'])
@app.route("/document/<id>/download", methods=['GET'])
@app.route("/document/<id>/update", methods=['POST', 'DELETE'])
def documentDetails(id):
  ret = {}
  if request.method == 'GET':
    doc = database.query_document(int(id))
    if request.path.endswith('/download'):
      if doc is None:
        abort(404)
      else:
        filename = os.path.join(COMPLETE_FOLDER, doc['filename'])
        return send_file(filename)
    else:
      if doc is None:
        ret['error'] = 'No such document'
      else:
        ret['result'] = doc
  elif request.method == 'DELETE':
    if request.path.endswith('/update'):
      json = request.get_json()
      if json is None:
        ret['error'] = 'Invalid delete request'
      elif 'tag' in json:
        if database.remove_tag(int(id), int(json['tag'])):
          ret['result'] = id
        else:
          ret['error'] = 'Unable to remove tag'
      else:
        ret['error'] = 'Invalid update request'
    else:
      # First, get info about the doc, since we need to delete it physically too
      doc = database.query_document(int(id))
      if doc is None:
        ret['error'] = 'No such document'
      else:
        if database.delete_document(int(id)):
          # Alright, delete the actual files too
          if deleteDocument(doc['filename']):
            ret['result'] = id
          else:
            ret['error'] = 'Database entry deleted but files remain'
        else:
          ret['error'] = 'No such document'
  elif request.method == 'POST':
    json = request.get_json()
    if json is None:
      ret['error'] = 'Invalid update request'
    elif 'category' in json:
      if database.assign_category(int(id), int(json['category'])):
        ret['result'] = id
      else:
        ret['error'] = 'Unable to update category'
    elif 'tag' in json:
      if database.assign_tag(int(id), int(json['tag'])):
        ret['result'] = id
      else:
        ret['error'] = 'Unable to add tag'
    else:
      ret['error'] = 'Invalid update request'
  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route("/document/<id>/page/<page>", methods=['GET'])
def documentGetPage(id, page):
  data = database.query_content(int(id), int(page))
  ret = {}
  if data:
    ret = {'result' : data}
  else:
    ret = {'error' : 'No such page'}
  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route("/document/<id>/small/<thumb>", methods=['GET'])
@app.route("/document/<id>/large/<thumb>", methods=['GET'])
def documentThumbnail(id, thumb):
  doc = database.query_document(int(id))
  if doc is None or int(thumb) >= doc['pages']:
    ret = {'error' : 'Invalid document or page'}
  elif '/small/' in request.path:
    filename = os.path.join(THUMB_FOLDER, doc['filename'][:-4], 'small%003d.jpg' % int(thumb))
    if os.path.exists(filename):
      return send_file(filename)
    else:
      generateThumbs(id)
      ret = {'error' : 'Thumbnail missing'}
  elif '/large/' in request.path:
    filename = os.path.join(THUMB_FOLDER, doc['filename'][:-4], 'large%003d.jpg' % int(thumb))
    if os.path.exists(filename):
      return send_file(filename)
    else:
      generateThumbs(id)
      ret = {'error' : 'Thumbnail missing'}
  else:
    ret = {'error' : 'Invalid thumb type'}
  res = jsonify(ret)
  res.status_code = 500
  return res

@app.route('/document/<id>/test', methods=['POST'])
@app.route('/document/test', methods=['POST'], defaults={'id':None})
def documentFilterTest(id):
  ret = {}
  json = request.get_json()
  if json is None or 'filter' not in json:
    ret['error']  = 'Invalid request'
  else:
    rec = database.test_filter(json['filter'], id);
    ret['result'] = []
    for r in rec:
      ret['result'].append(r)
  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
    logging.error('%s failed: %s' % (request.path, ret['error']))
  else:
    res.status_code = 200
  return res

@app.route('/category/<id>', methods=['GET', 'PUT', 'DELETE'])
@app.route('/category', methods=['PUT'], defaults={'id':None})
def categoryEdit(id):
  ret = {}
  json = request.get_json()
  #if json is None or ('name' not in json and 'id' not in json):
  #  ret['error'] = 'Invalid request, missing fields, got:' + repr(json)
  if id is not None:
    id = int(id)

  if request.method == 'GET':
    res = database.query_category(id)
    if res is None:
      ret['error'] = 'No such category'
    else:
      ret['result'] = res
  elif request.method == 'PUT' and json:
    if id:
      if database.set_category(id, json.get('name', None), json.get('filter', {})):
        ret['result'] = id
      else:
        ret['error'] = 'Unable to edit category';
    elif not id:
      id = database.add_category(json['name'], json.get('filter', '{}'))
      if id is None:
        ret['error'] = 'Unable to add category'
      else:
        ret['result'] = id
  elif request.method == 'DELETE':
    if not database.delete_category(id):
      ret['error'] = 'Unable to delete category'
    else:
      ret['result'] = id
  else:
    ret['error'] = 'Invalid request'
  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
    logging.error('%s failed: %s' % (request.path, ret['error']))
  else:
    res.status_code = 200
  return res

@app.route('/categories', methods=['GET'])
def categoriesList():
  ret = {'result' : []}

  for entry in database.query_categories():
    ret['result'].append(entry)

  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route("/documents", methods=['GET'])
def documentList():
  ret = {'result' : []}

  for entry in database.query_documents():
    ret['result'].append(entry)

  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route("/search", methods=['POST'])
def search():
  ret = {'result' : []}
  query = {'text':'', 'modifier': {'include' : [], 'exclude' : []}}
  json = request.get_json()
  if not json or 'text' not in json:
    ret = {'error' : 'Invalid request'}
  else:
    # First step is to break it apart and put it together again
    parts = shlex.split(json['text'])
    new = ""
    for part in parts:
      if ':' in part:
        logging.debug('"%s" is a keyword and will be removed from freeform' % part)
        s = part.split(':', 2)
        if s[0][0] == '-':
          query['modifier']['exclude'].append({s[0][1:] : s[1]})
        else:
          query['modifier']['include'].append({s[0] : s[1]})
      elif ' ' in part:
        new += ' "%s"' % part
      else:
        new += ' %s' % part
    if len(new):
      new = new[1:]
    query['text'] = new

    logging.debug('Query: ' + repr(query))

    for entry in database.query_all(query):
      ret['result'].append(entry)

  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route("/tags", methods=['GET'])
def tagList():
  ret = {'result' : []}

  for entry in database.query_tags():
    ret['result'].append(entry)

  res = jsonify(ret)
  if 'error' in ret:
    res.status_code = 500
  else:
    res.status_code = 200
  return res

@app.route('/tag/<id>', methods=['GET','PUT','DELETE'])
@app.route('/tag', methods=['PUT'], defaults={'id' : None})
def tagEdit(id):
  if id is not None:
    id = int(id)
  ret = {}
  json = request.get_json()
  if request.method == 'GET':
    data = database.query_tag(id)
    if data:
      ret['result'] = data
    else:
      ret['error'] = 'No such tag'
  elif request.method == 'PUT':
    if id:
      if not database.set_tag(id, json.get('name')):
        ret['error'] = 'Failed to update tag'
      else:
        ret['result'] = id
    else:
      id = database.add_tag(json['name'])
      if id is None:
        ret['error'] = 'Unable to add tag'
      else:
        ret['result'] = id
  elif request.method == 'DELETE':
    if not database.delete_tag(id):
      ret['error'] = 'Unable to delete tag'
    else:
      ret['result'] = id
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

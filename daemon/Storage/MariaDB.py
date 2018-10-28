# TODO:
#
import sys
import time
import threading
import logging
import datetime
import traceback
import random
import Storage

import mysql.connector
from mysql.connector import errorcode

class MariaDB:

  def __init__(self):
    pass

  def connect(self, user, pw, host, database):
    self.user = user
    self.password = pw
    self.host = host
    self.database = database
    return self.reconnect()

  def reconnect(self):
    try:
      self.cnx = mysql.connector.connect(user=self.user,
                                         password=self.password,
                                         host=self.host,
                                         database=self.database)
      return True
    except mysql.connector.Error as err:
      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        logging.error("Something is wrong with your user name or password")
        #logging.debug('User: ' + repr(self.user))
        #logging.debug('Pass: ' + repr(self.password))
        #logging.debug('Host: ' + repr(self.host))
        #logging.debug('DB  : ' + repr(self.database))
      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        logging.error("Database does not exist")
      else:
        logging.exception('Failed to connect')
    except:
      logging.exception('Failed to connect')
    return False

  def getCursor(self, dictionary=False, buffered=False):
    cursor = None
    try:
      cursor = self.cnx.cursor(buffered=buffered, dictionary=dictionary)
    except:
      if self.reconnect():
        cursor = self.cnx.cursor(buffered=buffered, dictionary=dictionary)
      else:
        logging.exception('Unable to reestablish connection with database')
    return cursor

  def validate(self):
    """
    Tests if the database is setup properly or if it needs to be installed
    or upgraded.

        0 = All is OK
        1 = Missing table(s)
        2 = Needs to upgrade
      255 = Things went terribly wrong
    """
    cursor = self.getCursor(buffered=True)
    for table in [ 'documents', 'pages', 'categories', 'tags', 'tagmap' ]:
      query = ("DESCRIBE " + table)
      try:
        cursor.execute(query)
      except mysql.connector.Error as err:
        cursor.close()
        if err.errno == errorcode.ER_NO_SUCH_TABLE:
          return Storage.VALIDATION_NOT_SETUP
        else:
          logging.exception('Failed to validate')
          return Storage.VALIDATION_ERROR
    cursor.close()
    return Storage.VALIDATION_OK

  def setup(self, force):
    if force:
      cursor = self.getCursor(buffered=True)
      for table in [ 'documents', 'pages', 'categories', 'tags', 'tagmap', 'contents' ]:
        query = ("DROP TABLE " + table)
        try:
          logging.info(query)
          cursor.execute(query)
        except mysql.connector.Error as err:
          pass
      cursor.close()

    if self.validate() != Storage.VALIDATION_NOT_SETUP:
      logging.error('Database is not in a state where it can be setup')
      return False

    sql = [
      'CREATE TABLE documents (id INT PRIMARY KEY AUTO_INCREMENT, category INT, scanned INT NOT NULL, received INT, pages INT NOT NULL, filename TEXT NOT NULL, hash VARCHAR(255) NOT NULL)',
      'CREATE TABLE pages (id INT NOT NULL, page INT NOT NULL, ocr BOOLEAN NOT NULL, blankness INT NOT NULL, degrees INT NOT NULL, confidence REAL NOT NULL, colors INT NOT NULL, UNIQUE KEY page (page, id))',
      'CREATE TABLE contents (id INT NOT NULL, page INT NOT NULL, content LONGTEXT NOT NULL, FULLTEXT INDEX (content), UNIQUE KEY page (page, id))',
      'CREATE TABLE categories (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(128) NOT NULL, filter TEXT NOT NULL DEFAULT "")',
      'CREATE TABLE tags (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(128) NOT NULL, UNIQUE KEY name (name))',
      'CREATE TABLE tagmap (tag INT NOT NULL, document INT NOT NULL, UNIQUE KEY tag (tag, document))'
    ]

    cursor = self.getCursor(buffered=True)
    for s in sql:
      try:
        cursor.execute(s)
      except mysql.connector.Error as err:
        logging.exception('Failed to execute: ' + s)
        cursor.close()
        return False
    cursor.close()
    return True

  def disconnect(self):
    self.cnx.close()

  def prepare(self):
    return True

  def add_document(self, category, scanned, received, pages, filename, hashstr):
    query = 'INSERT INTO documents (category, scanned, received, pages, filename, hash) VALUES (%s, %s, %s, %s, %s, %s)'
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query, (category, scanned, received, pages, filename, hashstr))
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add document: ' + repr(err));
    finally:
      cursor.close()
    return None

  def add_page(self, document, page, ocr, blankness, degrees, confidence, colors, blob):
    query = 'INSERT INTO pages (id, page, ocr, blankness, degrees, confidence, colors) VALUES (%s, %s, %s, %s, %s, %s, %s)'
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query, (document, page, ocr, blankness, degrees, confidence, colors))
      self.cnx.commit()
      cursor.close()
      query = 'INSERT INTO contents (id, page, content) VALUES (%s, %s, %s)'
      cursor = self.getCursor(buffered=True)
      cursor.execute(query, (document, page, blob))
      self.cnx.commit()
      cursor.close()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to add page: ' + repr(err));
    finally:
      cursor.close()
    return False

  def delete_document(self, document):
    query = 'DELETE FROM documents WHERE id = %s' % document
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      cursor.close()
      query = 'DELETE FROM pages WHERE id = %s' % document
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      cursor.close()
      query = 'DELETE FROM contents WHERE id = %s' % document
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      cursor.close()
      query = 'DELETE FROM tagmap WHERE document = %s' % document
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete document: ' + repr(err));
    finally:
      cursor.close()
    return False

  def add_category(self, name, filter):
    name = name.lower().strip()
    if len(name) == 0:
      return False
    query = 'INSERT INTO categories (name, filter) VALUES (%s, %s)'
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query, (name.lower(), filter))
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add category: ' + repr(err));
    finally:
      cursor.close()
    return None

  def set_category(self, id, name, filter):
    if name is None and filter is None:
      return True
    if name is not None:
      name = name.lower().strip()
      if len(name) == 0:
        return False

    query = 'UPDATE categories SET'
    if name is not None:
      query += ' name="%s"' % self.cnx.converter.escape(name)
    if name and filter:
      query += ', '
    if filter is not None:
      query += ' filter="%s"' % self.cnx.converter.escape(filter)
    query += ' WHERE id=%d' % id
    logging.debug('Query: ' + query)
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to edit category: ' + repr(err));
    finally:
      cursor.close()
    return False

  def delete_category(self, id):
    query = 'DELETE FROM categories WHERE id = %d' % id
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      cursor.close()
      query = 'UPDATE documents SET category = NULL WHERE id = %d' % id
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete category: ' + repr(err));
    finally:
      cursor.close()
    return False

  def assign_category(self, document, category):
    # Check that there is such a category!
    cursor = self.getCursor(buffered=True)
    try:
      # Zero is allowed since it's no category
      if category > 0:
        query = 'SELECT id FROM categories WHERE id = %d' % category
        cursor.execute(query)
        self.cnx.commit()
        if cursor.rowcount != 1:
          return False
      query = 'UPDATE documents SET category = %d WHERE id = %d' % (category, document)
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to update category: ' + repr(err));
    finally:
      cursor.close()
    return False

  def assign_tag(self, document, tag):
    cursor = self.getCursor(buffered=True)
    try:
      query = 'SELECT id FROM tags WHERE id = %d' % tag
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      query = 'SELECT id FROM documents WHERE id = %d' % document
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      query = 'INSERT INTO tagmap (tag, document) VALUES (%d, %d)' % (tag, document)
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      if err[0] == 1062: # Special case, already have tag, swallow error
        return True
      logging.exception('Failed to assign tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def remove_tag(self, document, tag):
    cursor = self.getCursor(buffered=True)
    try:
      # Zero is allowed since it's no category
      query = 'DELETE FROM tagmap WHERE tag=%d and document=%d' % (tag, document)
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to remove tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def clear_tag(self, document):
    cursor = self.getCursor(buffered=True)
    try:
      # Zero is allowed since it's no category
      query = 'DELETE FROM tagmap WHERE document=%d' % (document)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to remove tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def add_tag(self, name):
    name = name.lower().strip()
    if len(name) == 0:
      return False
    query = 'INSERT INTO tags (name) VALUES ( "%s" )' % name
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add tag, sql: "%s" name="%s"' % (query, name));
    finally:
      cursor.close()
    return None

  def set_tag(self, id, name):
    name = name.lower().strip()
    if len(name) == 0:
      logging.error('Empty name was provided')
      return False
    query = 'UPDATE tags SET name="%s" WHERE id=%d' % (name, int(id))
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to edit tag, sql: "%s" name="%s"' % (query, name));
    finally:
      cursor.close()
    return False

  def delete_tag(self, id):
    query = 'DELETE FROM tags WHERE id = %d' % id
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      cursor.close()
      query = 'DELETE FROM tagmap WHERE tag = %d' % id
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def _query_with_iterator(self, query, process=None):
    cursor = self.getCursor(dictionary=True, buffered=True)
    try:
      cursor.execute(query)
      return Iterator(cursor, process)
    except mysql.connector.Error as err:
      logging.exception('Query failed');
    cursor.close()
    return None

  def query_tags(self):
    return self._query_with_iterator('SELECT * FROM tags ORDER BY name')

  def query_tag(self, id):
    data = self._query_with_iterator('SELECT * FROM tags WHERE id = %d' % id)
    if data is not None:
      data = data.next()
    return data

  def query_categories(self):
    return self._query_with_iterator('SELECT categories.*, COUNT(documents.id) AS uses FROM categories LEFT JOIN documents ON (documents.category = categories.id) GROUP BY categories.id ORDER BY name')

  def query_category(self, id):
    data = self._query_with_iterator('SELECT * FROM categories WHERE id = %d' % id)
    if data is not None:
      data = data.next()
    return data

  def query_hash(self, hashstr):
    data = self._query_with_iterator('SELECT * FROM documents WHERE hash = "%s"' % hashstr)
    if data is not None and data.size() > 0:
      data = data.next()
    else:
      data = None
    return data

  def query_document(self, id):
    data = None
    result = self._query_with_iterator("""
      SELECT
        documents.*,
        categories.name AS cname,
        GROUP_CONCAT(tags.id ORDER BY tags.name ASC SEPARATOR ',') AS tags
      FROM
        documents
        LEFT JOIN categories ON (documents.category = categories.id)
        LEFT JOIN tagmap ON (documents.id = tagmap.document)
        LEFT JOIN tags ON (tags.id = tagmap.tag)
      WHERE
        documents.id = %d
      GROUP BY
        documents.id
    """ % id, self.cleanDocumentInfo)
    try:
      data = result.next()
      # Finally, load page info (not the text, just details)
      result = self._query_with_iterator('SELECT * FROM pages WHERE id = %d' % id)
      data['page'] = []
      for t in result:
        data['page'].append(t)
      if len(data['page']) == 0:
        del data['page']
    except:
      logging.exception('Error getting document')
    return data

  def update_document(self, id, field, value=None):
    cursor = self.getCursor(dictionary=True, buffered=True)
    if value is None:
      query = 'UPDATE documents SET '
      for k in field:
        query += '%s = %s, ' % (k, field[k])
      query = query[:-2] + ' WHERE id = %d' % id
    else:
      query = 'UPDATE documents SET %s = %s WHERE id = %d' % (field, value, id)
    try:
      cursor.execute(query)
      self.cnx.commit()
    except mysql.connector.Error as err:
      logging.exception('Query failed');
      logging.error('Query was: "%s"' % query)
      return False
    finally:
      cursor.close()
    return True

  def query_pages(self, id):
    data = None
    result = self._query_with_iterator('SELECT * FROM pages WHERE id = %d ORDER BY page' % id)
    return result

  def query_content(self, id, page):
    data = None
    result = self._query_with_iterator('SELECT content FROM contents WHERE id = %d AND page = %d' % (id, page))
    if result:
      result = result.next()
      data = result['content']
    return data

  def cleanDocumentInfo(self, record):
    if 'category' in record and record['category'] == 0:
      del record['category']
    else:
      record['category'] = {'id' : record['category'], 'name' : record['cname']}
    del record['cname']
    if 'scanned' in record and record['scanned'] == 0:
      del record['scanned']
    if 'received' in record and record['received'] == 0:
      del record['received']

  def test_filter(self, filter, document=None):
    if document is None:
      query = """SELECT
                  contents.id AS document,
                  contents.page AS page,
                  MATCH (contents.content) AGAINST ("%s" IN BOOLEAN MODE) AS score
                 FROM contents
                 WHERE
                  MATCH (contents.content) AGAINST ("%s" IN BOOLEAN MODE)
                 ORDER BY contents.id, contents.page
              """
    else:
      query = """SELECT
                  contents.id AS document,
                  contents.page AS page,
                  MATCH (contents.content) AGAINST ("%s" IN BOOLEAN MODE) AS score
                 FROM contents
                 WHERE
                  id = %s AND
                  MATCH (contents.content) AGAINST ("%s" IN BOOLEAN MODE)
                 ORDER BY contents.id, contents.page
              """
    cursor = self.getCursor(dictionary=True, buffered=True)
    try:
      if document is None:
        cursor.execute(query, (filter, filter))
      else:
        cursor.execute(query, (filter, document, filter))
      return Iterator(cursor)
    except mysql.connector.Error as err:
      logging.exception('Failed to query data: ' + repr(err));
      logging.error('Query was "%s"' % query)
      logging.error('Keys contained: ' + repr(keys))
    cursor.close()
    return Iterator(None, 'Error performing query')

  def generateDateQuery(self, field, value):
    """ Will handle cases where only year or month is provided, as well as more complex versions
        where it's a range. The format looks like this:
          YYYY (the entire year)
          YYYY-MM (that month)
          YYYY-MM-DD (that day)
        To make a range, simply add a colon and enter next date.
        Note that the format must be identical when using range, so:
          YYYY:YYYY
          YYYY-MM:YYYY-MM
          YYYY-MM-DD:YYYY-MM-DD
        not
          YYYY:YYYY-MM
        or the likes, that will be rejected
        The order of date is not important in the range, either way works
    """
    start = value.split('-')
    end = None
    if "=" in value:
      (start, end) = value.split('=',1)
      start = start.split('-')
      end = end.split('-')

    result = ''
    if end is not None and len(start) != len(end):
      logging.error('Cannot generate date query using %s', value)
    elif len(start) == 3: # Day
      if end is None:
        result = 'AND UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) = UNIX_TIMESTAMP("%s")' % (field, '-'.join(start))
      else:
        result = 'AND (UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) >= UNIX_TIMESTAMP("%s") AND UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) <= UNIX_TIMESTAMP("%s"))' % (field, '-'.join(start), field, '-'.join(end))
    elif len(start) == 2: # Month
      if end is None:
        result = 'AND (UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) >= UNIX_TIMESTAMP("%s-01") AND UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) <= UNIX_TIMESTAMP(LAST_DAY("%s-01")))' % (field, '-'.join(start), field, '-'.join(start))
      else:
        result = 'AND (UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) >= UNIX_TIMESTAMP("%s-01") AND UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) <= UNIX_TIMESTAMP(LAST_DAY("%s-01")))' % (field, '-'.join(start), field, '-'.join(end))
    elif len(start) == 1: # Year
      if end is None:
        result = 'AND (UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) >= UNIX_TIMESTAMP("%s-01-01") AND UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) <= UNIX_TIMESTAMP(LAST_DAY("%s-12-01")))' % (field, '-'.join(start), field, '-'.join(start))
      else:
        result = 'AND (UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) >= UNIX_TIMESTAMP("%s-01-01") AND UNIX_TIMESTAMP(DATE(FROM_UNIXTIME(%s))) <= UNIX_TIMESTAMP(LAST_DAY("%s-12-01")))' % (field, '-'.join(start), field, '-'.join(end))
    logging.debug("Additional query: " + repr(result))
    return result

  def query_all(self, keys):
    qfield = """
      documents.*,
      categories.name AS cname,
      pages.*,
      GROUP_CONCAT(tags.id ORDER BY tags.name ASC SEPARATOR ',') AS tags
    """

    qtables = """
      pages
      LEFT JOIN documents ON (documents.id = pages.id)
      LEFT JOIN categories ON (categories.id = documents.category)
      LEFT JOIN tagmap ON (documents.id = tagmap.document)
      LEFT JOIN tags ON (tags.id = tagmap.tag)
      LEFT JOIN contents ON (contents.id = pages.id AND contents.page = pages.page)
    """

    qwhere = ''

    qgroup = """
      documents.id
    """

    qorder = """
      score DESC,
      documents.received DESC,
      documents.id,
      pages.page
    """

    if keys['text'] == '' and len(keys['modifier']['include']) == 0 and len(keys['modifier']['exclude']) == 0:
      return Iterator(None, 'No query')
    elif keys['text'] == '':
      qfield += ', 1 AS score'
    else:
      qfield += ',MATCH (contents.content) AGAINST ("%s" IN BOOLEAN MODE) AS score' % self.cnx.converter.escape(keys['text'])
      qwhere += 'MATCH (contents.content) AGAINST ("%s" IN BOOLEAN MODE)'  % self.cnx.converter.escape(keys['text'])

    # Add any special modifiers...
    for include in keys['modifier']['include']:
      if 'catid' in include:
        qwhere += 'AND documents.category = %d ' % int(include['catid'])
      elif 'added' in include:
        qwhere += self.generateDateQuery('documents.scanned', include['added']) #'AND DATE(FROM_UNIXTIME(documents.scanned)) = "%s" ' % include['added']
      elif 'dated' in include:
        qwhere += self.generateDateQuery('documents.received', include['dated']) #'AND DATE(FROM_UNIXTIME(documents.received)) = "%s" ' % include['dated']
      elif 'contains' in include:
        qwhere += 'AND contents.content LIKE "%%%s%%" ' % include['contains']
      elif 'blank' in include:
        if include['blank'] == 'yes':
          qwhere += 'AND pages.blankness < 200'
        else:
          qwhere += 'AND pages.blankness > 199'

    # Allow changing how we sort
    if 'order' in keys:
      if keys['order'] == 'added':
        qorder = """
        documents.received DESC,
        score DESC,
        documents.id,
        pages.page
        """



    # Strip first part to make sure we're a query
    if qwhere.startswith('AND '):
      qwhere = qwhere[4:]
    elif qwhere.startswith('OR '):
      qwhere = qwhere[3:]

    query = 'SELECT ' + qfield + ' FROM ' + qtables + ' WHERE ' + qwhere + ' GROUP BY ' + qgroup + ' ORDER BY ' + qorder

    logging.debug("Final query:");
    print(query)

    cursor = self.getCursor(dictionary=True, buffered=True)
    try:
      cursor.execute(query) # , (keys['text']))
      return Iterator(cursor, self.cleanDocumentInfo)
    except mysql.connector.Error as err:
      logging.exception('Failed to query data: ' + repr(err));
      logging.error('Query was "%s"' % query)
      logging.error('Keys contained: ' + repr(keys))
    cursor.close()
    return Iterator(None, 'Error performing query')

  def query_documents(self, tags=None, categories=None, sortby=None):
    # Build the query
    query = """ SELECT
                  documents.*,
                  categories.name AS cname,
                  GROUP_CONCAT(tags.id ORDER BY tags.name ASC SEPARATOR ',') AS tags
                FROM
                  documents
                  LEFT JOIN categories ON (documents.category = categories.id)
                  LEFT JOIN tagmap ON (tagmap.document = documents.id)
                  LEFT JOIN tags ON (tags.id = tagmap.tag)
                GROUP BY
                  documents.id
            """
    if tags:
      query += ' LEFT JOIN tagmap ON tagmap.document = documents.id WHERE tagmap.id IN ('
      for tag in tags:
        query += '%d' % tag
        if tag != tags[len(tags)-1]:
          query += ', '
      query += ')'

    if not tags and categories:
      query += ' WHERE'

    if categories:
      query += ' category IN ('
      for category in categories:
        query += '%d' % category
        if category != categories[len(categories)-1]:
          query += ', '
      query += ')'

    if sortby:
      query += ' ORDER BY %s' % sortby
    else:
      query += ' ORDER BY COALESCE(scanned, NULLIF(received,0)) DESC'
#      query += ' ORDER BY COALESCE(NULLIF(received,0), scanned) DESC, COALESCE(scanned, NULLIF(received,0)) DESC'

    #logging.debug('Query statement: ' + query)

    cursor = self.getCursor(dictionary=True, buffered=True)
    try:
      cursor.execute(query)
      return Iterator(cursor, self.cleanDocumentInfo, None)
    except mysql.connector.Error as err:
      logging.exception('Failed to query data: ' + repr(err));
    cursor.close()
    return Iterator(None, 'Error performing query')

class Iterator:
  def __init__(self, resultset, process=None, error=None):
    self.cursor = resultset
    self.error = error
    self.process = process

  def getError(self):
    """
    Returns any potential error, if no error condition exist,
    it will return None
    """
    return self.error

  def __iter__(self):
    return self

  def __next__(self):
    return self.next()

  def size(self):
    if self.error is not None:
      raise StopIteration
    elif self.cursor is None:
      logging.warning('Cursor was none')
      raise StopIteration
    else:
      return self.cursor.rowcount

  def next(self):
    """
    Advances to the next record, returning current
    Record is a dict

    If no more record exists, the function returns None
    """
    if self.error is not None:
      raise StopIteration
    if self.cursor is not None:
      rec = self.cursor.fetchone()
    else:
      logging.warning('Cursor was None')
      rec = None
    if rec is None:
      raise StopIteration
    elif self.process is not None:
      self.process(rec)
    return rec

  def release(self):
    """
    Early bailout, after calling this function, the iterator
    resources are freed and you should not use it anymore.
    """
    if self.error is not None:
      return
    self.error = 'Iterator is released'
    self.cursor.close()
    self.cursor = None
    return

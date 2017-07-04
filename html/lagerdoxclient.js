LagerDoxClient = function(serverAddress) {
  this.cfgAddress = serverAddress;
  this.tagCache = null;

  this.execServer = function(addr, successFunction, errorFunction, reqType, data) {
    if (errorFunction == undefined)
      errorFunction = this.genericError;
    if (reqType == undefined)
      reqType = 'GET';
    var req = {
      url: this.cfgAddress + addr,
      type: reqType,
      success: function(obj, info, t) {
        successFunction(obj);
      },
      error: function(obj, info, t) {
        console.log(obj);
        if (obj.readyState == 0) {
          info = 'lagerDOX backend is not responding. Unable to process your request';
        }
        errorFunction(info);
      }
    }
    if (data != undefined) {
      req['data'] = JSON.stringify(data);
      req['contentType'] = 'application/json; charset=utf-8';
      req['dataType'] = 'json';
    }
    $.ajax(req);
  }

  this.resolveTags = function(doc, resultFunction, errorFunction) {
    var found = true;
    if ('tags' in doc && doc['tags'] != null) {
      if (self.tagCache == null)
        return false;
      // Translate this into a map instead
      var result = [];
      var tags = doc['tags'].split(',');
      for (var tag in tags) {
        found = false;
        for (var s in self.tagCache) {
          if (self.tagCache[s]['id'] == tags[tag]) {
            result.push(self.tagCache[s]);
            found = true;
            break;
          }
        }
        if (!found)
          break;
      }
      if (found)
        doc['tags'] = result;
    }
    return found;
  }

  this.loadTagCache = function(doneFunction) {
    this.getTags(function(tags) {
      self.tagCache = tags['result'];
      doneFunction();
    }, function(){});
  }

  this.getDocuments = function(resultFunction, errorFunction) {
    self = this;
    this.execServer('/documents', function(result) {
      var needRefresh = false;
      for (var d in result["result"]) {
        var doc = result["result"][d];
        if ('received' in doc)
          result["result"][d]['received'] = new Date(doc['received']*1000);
        if ('scanned' in doc)
          result["result"][d]['scanned'] = new Date(doc['scanned']*1000);
        if (!self.resolveTags(result['result'][d]))
          needRefresh = true;
      }
      if (needRefresh) {
        self.loadTagCache(function() {
          for (var d in result["result"]) {
            self.resolveTags(result['result'][d]);
          }
          resultFunction(result);
        })
      } else
        resultFunction(result);
    }, errorFunction);
  }

  this.getDocument = function(id, resultFunction, errorFunction) {
    self = this;
    this.execServer('/document/' + id, function(result) {
      if ('received' in result['result'] && result['result']['received'] > 0)
        result['result']['received'] = new Date(result['result']['received']*1000);
      if ('scanned' in result['result'] && result['result']['scanned'] > 0)
        result['result']['scanned'] = new Date(result['result']['scanned']*1000);
      if (!self.resolveTags(result['result'])) {
        self.loadTagCache(function() {
          self.resolveTags(result['result']);
          resultFunction(result);
        })
      } else
        resultFunction(result);
    }, errorFunction);
  }

  this.getTags = function(resultFunction, errorFunction) {
    this.execServer('/tags', function(result) {
      resultFunction(result);
    }, errorFunction);
  }

  this.getTag = function(id, resultFunction, errorFunction) {
    this.execServer('/tag/' + id, function(result) {
      resultFunction(result);
    }, errorFunction);
  }

  this.getStatus = function(resultFunction, errorFunction) {
    this.execServer('/status', function(result) {
      if ('failed' in result) {
        for (var i = 0; i != result['failed'].length; ++i)
          result['failed'][i]['time'] = new Date(result['failed'][i]['time']*1000);
      }
      resultFunction(result);
    }, errorFunction);
  }

  this.getCategories = function(resultFunction, errorFunction) {
    this.execServer('/categories', function(result) {
      resultFunction(result);
    }, errorFunction);
  }

  this.getCategory = function(id, resultFunction, errorFunction) {
    this.execServer('/category/' + parseInt(id), function(result) {
      resultFunction(result);
    }, errorFunction);
  }

  this.genericError = function(result) {
    alert(result);
  }

  this.deleteDocument = function(id, resultFunction, errorFunction) {
    this.execServer('/document/' + id, resultFunction, errorFunction, 'DELETE');
  }

  this.addCategory = function(name, filter, resultFunction, errorFunction) {
    this.execServer('/category', resultFunction, errorFunction, 'PUT', {'name':name,'filter':filter});
  }

  this.editCategory = function(id, name, filter, resultFunction, errorFunction) {
    this.execServer('/category/' + id, resultFunction, errorFunction, 'PUT', {'name':name,'filter':filter});
  }

  this.deleteCategory = function(id, resultFunction, errorFunction) {
    this.execServer('/category/' + id, resultFunction, errorFunction, 'DELETE');
  }

  this.deleteTag = function(id, resultFunction, errorFunction) {
    this.execServer('/tag/' + id, resultFunction, errorFunction, 'DELETE');
  }

  this.addTag = function(name, resultFunction, errorFunction) {
    this.execServer('/tag', resultFunction, errorFunction, 'PUT', {'name':name});
  }

  this.editTag = function(id, name, resultFunction, errorFunction) {
    this.execServer('/tag/' + id, resultFunction, errorFunction, 'PUT', {'name':name});
  }

  this.getPageContent = function(id, page, resultFunction, errorFunction) {
    this.execServer('/document/' + id + '/page/' + page, resultFunction, errorFunction);
  }

  this.assignCategory = function(doc, cat, resultFunction, errorFunction) {
    this.execServer('/document/' + doc + '/category/' + cat, resultFunction, errorFunction, 'PUT');
  }

  this.removeCategory = function(doc, resultFunction, errorFunction) {
    this.execServer('/document/' + doc + '/category', resultFunction, errorFunction, 'DELETE');
  }

  this.assignTag = function(doc, tag, resultFunction, errorFunction) {
    this.execServer('/document/' + doc + '/tag/' + tag, resultFunction, errorFunction, 'PUT');
  }

  this.removeTag = function(doc, tag, resultFunction, errorFunction) {
    this.execServer('/document/' + doc + '/tag/' + tag, resultFunction, errorFunction, 'DELETE');
  }

  this.clearTags = function(doc, resultFunction, errorFunction) {
    this.execServer('/document/' + doc + '/tag', resultFunction, errorFunction, 'DELETE');
  }

  this.search = function(text, resultFunction, errorFunction) {
    this.execServer('/search', function (result) {
      for (var i in result['result']) {
        if ('received' in result['result'][i] && result['result'][i]['received'] > 0)
          result['result'][i]['received'] = new Date(result['result'][i]['received']*1000);
        if ('scanned' in result['result'][i] && result['result'][i]['scanned'] > 0)
          result['result'][i]['scanned'] = new Date(result['result'][i]['scanned']*1000);
      }
      resultFunction(result);
    }, errorFunction, 'POST', {'text':text});
  }

  this.testFilter = function(filter, resultFunction, errorFunction) {
    this.execServer('/document/test', resultFunction, errorFunction, 'POST', {'filter':filter});
  }
}

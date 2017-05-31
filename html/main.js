LagerDoxClient = function() {
  this.cfgAddress = "http://magi.sfo.sensenet.nu:7000/";

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
        console.log("ResultERR: " + info + " from calling " + addr);
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

  this.getDocuments = function(resultFunction, errorFunction) {
    this.execServer('/documents', function(result) {
      for (var d in result["result"]) {
        var doc = result["result"][d];
        if ('received' in doc)
          result["result"][d]['received'] = new Date(doc['received']*1000);
        if ('scanned' in doc)
          result["result"][d]['scanned'] = new Date(doc['scanned']*1000);
      }
      resultFunction(result);
    }, errorFunction);
  }

  this.getDocument = function(id, resultFunction, errorFunction) {
    this.execServer('/document/' + id, function(result) {
      if ('received' in result && result['received'] > 0)
        result['received'] = new Date(result['received']*1000);
      if ('scanned' in result && result['scanned'] > 0)
        result['scanned'] = new Date(result['scanned']*1000);
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
    alert("AJAX call failed!\nError:" + result['error']);
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
          result[i]['received'] = new Date(result['result'][i]['received']*1000);
        if ('scanned' in result['result'][i] && result['result'][i]['scanned'] > 0)
          result['result'][i]['scanned'] = new Date(result['result'][i]['scanned']*1000);
      }
      resultFunction(result);
    }, errorFunction, 'POST', {'text':text});
  }
}

$( document ).ready(function() {
  client = new LagerDoxClient();

  function showDocs() {
    history.replaceState(null, "upload", "?section=documents");
    $('#content').empty();
    client.getDocuments(function(obj) {
      var comp = Handlebars.getTemplate('document_list');
      $('#content').html(comp({'server' : 'magi.sfo.sensenet.nu', 'items' : obj['result']}));
      $('.document_item').on('click', '#item_delete', function(e) {
        deleteDoc(e.target.dataset.id, function() { $(e.delegateTarget).remove(); });
      });
      $('.document_item').on('click', '#item_download', function(e) {
        downloadDoc(e.target.dataset.id);
      });
    });
  }

  function downloadDoc(id) {
    window.location.href="http://magi.sfo.sensenet.nu:7000/document/" + id + "/download";
  }

  function deleteDoc(id, success) {
    if (confirm('Are you sure you want to delete this document? It cannot be undone!')) {
      client.deleteDocument(id, function(result) {
        if (success)
          success(result);
      });
    }
  }

  function deleteCategory(id, success) {
    if (confirm('Are you sure you want to delete this category? It cannot be undone!')) {
      client.deleteCategory(id, function(result) {
        if (success)
          success();
      });
    }
  }

  function deleteTag(id, success) {
    if (confirm('Are you sure you want to delete this tag? It cannot be undone!')) {
      client.deleteTag(id, function(result) {
        if (success)
          success();
      });
    }
  }

  function showDoc(id) {
    history.replaceState(null, "upload", "?section=documents&view=" + id);
    $('#content').empty();
    client.getDocument(id, function(obj) {
      var comp = Handlebars.getTemplate('document');
      obj['server'] = 'magi.sfo.sensenet.nu';
      $('#content').html(comp(obj));
      $('#item_delete').on('click', function(e) {
        deleteDoc(e.target.dataset.id, function() { showDocs(); });
      });
      $('#item_download').on('click', function(e) {
        downloadDoc(e.target.dataset.id);
      });
      $('#item_category').on('click', function(e) {
        var comp = Handlebars.getTemplate('category_selectbox');
        var doc = e.target.dataset.id;
        client.getCategories(function(result) {
          $('#item_category').replaceWith(comp(result));
          $('#category_selectbox').on('change', function(e) {
            var cat = $(e.target).val();
            if (cat != "") {
              client.assignCategory(doc, cat, function() {
                showDoc(doc);
              });
            } else {
              client.removeCategory(doc, function() {
                showDoc(doc);
              });
            }
          });
        });
      });
      $('#item_tag').on('click', function(e) {
        var comp = Handlebars.getTemplate('tag_selectbox');
        var doc = e.target.dataset.id;
        client.getTags(function(result) {
          $('#item_tag').replaceWith(comp(result));
          $('#tag_selectbox').on('change', function(e) {
            var tag = $(e.target).val();
            if (tag != "") {
              client.assignTag(doc, tag, function() {
                showDoc(doc);
              });
            } else
              showDoc(doc);
          });
        });
      });
      $('.document_info').on('click', '#tag_delete', function(e) {
        client.removeTag(e.target.dataset.id, e.target.dataset.tag, function(result) {
          $(e.target).remove();
        });
      });
      $('.page').on('click', 'img', function(e) {
        client.getPageContent(e.target.dataset.id, e.target.dataset.page, function(result) {
          console.log(e);
          $(e.delegateTarget).html('<pre>' + result['result'] + '</pre>');
        });
      });
    }, function() {
      showDocs();
    });
  }

  function showTags() {
    history.replaceState(null, "upload", "?section=tags");
    $('#content').empty();
    client.getTags(function(obj) {
      var comp = Handlebars.getTemplate('tags');
      $('#content').html(comp(obj));
      $('.tag').on('click', '#tag_edit', function(e) {
        client.getTag(e.target.dataset.id, function(result) {
          $('#add').hide();

          $('#name').val(result['result']['name']);
          $('#name').data('org', $('#name').val());

          $('#save').data('id', result['result']['id']);
          $('#save').show();
        });
      });
      $('.tag').on('click', '#tag_delete', function(e) {
        deleteTag(e.target.dataset.id, function() { e.delegateTarget.remove(); });
      });
      $('#add').on('click', function(e) {
        if ($('#name').val().trim() == '') {
          alert('No name provided');
        } else {
          client.addTag($('#name').val(), function(result) {
            showTags();
          });
        }
      });
      $('#save').on('click', function(e) {
        if ($('#name').val().trim() == '') {
          alert('No name provided');
        } else if ($('#name').val().trim() == $('#name').data('org')) {
          showTags();
        } else if ($('#save').data('id') == undefined) {
          console.log('Target is undefined');
          console.log(e);
          showTags();
        } else {
          client.editTag($('#save').data('id'), $('#name').val(), function(result) {
            showTags();
          });
        }
      });
    });
  }


  function showStatus() {
    if ($('.status').length)
      return;

    history.replaceState(null, "upload", "?section=status");
    $('#content').empty();
    var comp = Handlebars.getTemplate('status');
    $('#content').html('<div class="status"></div>');
    refreshStatus(comp);
  }

  function refreshStatus(comp) {
    client.getStatus(function(obj) {
      if ($('.status').length) {
        $('#content').html(comp(obj));
        setTimeout(function() { refreshStatus(comp); }, 1000);
      }
    });
  }

  function showCategories() {
    history.replaceState(null, "upload", "?section=categories");
    $('#content').empty();
    client.getCategories(function(obj) {
      var comp = Handlebars.getTemplate('categories');
      $('#content').html(comp(obj));
      $('.category').on('click', '#category_edit', function(e) {
        client.getCategory(e.target.dataset.id, function(result) {
          $('#add').hide();

          $('#name').val(result['result']['name']);
          $('#name').data('org', $('#name').val());

          var data = JSON.parse(result['result']['filter']);
          var keys = '';
          if ('keywords' in data) {
            for (var e in data['keywords']) {
              keys += ' ' + data['keywords'][e];
            }
          }
          $('#keywords').val(keys.trim());
          $('#keywords').data('org', $('#keywords').val());

          $('#save').data('id', result['result']['id']);
          $('#save').show();
        });
      });
      $('.category').on('click', '#category_delete', function(e) {
        deleteCategory(e.target.dataset.id, function() { e.delegateTarget.remove(); });
      });
      $('#add').on('click', function(e) {
        if ($('#name').val().trim() == '') {
          alert('No name provided');
        } else {
          client.addCategory($('#name').val(), JSON.stringify({'keywords':$('#keywords').val().split(/\s+/)}), function(result) {
            showCategories();
          });
        }
      });
      $('#save').on('click', function(e) {
        if ($('#name').val().trim() == '') {
          alert('No name provided');
        } else if ($('#name').val().trim() == $('#name').data('org') && $('#keywords').val().trim() == $('#keywords').data('org')) {
          showCategories();
        } else if ($('#save').data('id') == undefined) {
          console.log('Target is undefined');
          console.log(e);
          showCategories();
        } else {
          client.editCategory($('#save').data('id'), $('#name').val(), JSON.stringify({'keywords':$('#keywords').val().split(/\s+/)}), function(result) {
            showCategories();
          });
        }
      });
    });
  }

  function showUpload() {
    history.replaceState(null, "upload", "?section=upload");
    $('#content').empty();
    var comp = Handlebars.getTemplate('upload');
    $('#content').html(comp({'server':'magi.sfo.sensenet.nu:7000'}));
    $('#file').fileupload({
      progressall: function (e, data) {
        var progress = parseInt(data.loaded / data.total * 100, 10);
        $('#progress .bar').css(
          'width',
          progress + '%'
        );
        if (data.loaded == data.total) {
          showStatus();
        }
      },
    });
  }

  function showSearch() {
    var q = getUrlParameter('q');
    if (q != null) {
      history.replaceState(null, "search", "?section=search&q=" + encodeURIComponent(q));
    } else {
      history.replaceState(null, "search", "?section=search");
    }
    $('#content').empty();
    var comp = Handlebars.getTemplate('search');
    $('#content').html(comp());
    $('#query').val(q);
    search(q);

    $('#query').on('keypress', function(event) {
      if(event.keyCode == 13) { // 13 = Enter Key
        search($('#query').val());
      }
    });

    $('#search').on('click', function() {
      search($('#query').val());
    });
  }

  function search(query) {
    history.replaceState(null, "search", "?section=search&q=" + encodeURIComponent(query));
    $('#results').empty();
    client.search(query, function(result) {
      console.log(result);
      var comp = Handlebars.getTemplate('search_result');
      $('#results').html(comp({'server' : 'magi.sfo.sensenet.nu', 'items' : result['result']}));
    })
  }

  function getUrlParameter(sParam) {
    // See http://www.jquerybyexample.net/2012/06/get-url-parameters-using-jquery.html
    var sPageURL = decodeURIComponent(window.location.search.substring(1)),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
      sParameterName = sURLVariables[i].split('=');

      if (sParameterName[0] === sParam) {
        return sParameterName[1] === undefined ? true : sParameterName[1];
      }
    }
    return null;
  }

  // Add our magic date hlper!
  Handlebars.registerHelper('dtos', function(date) {
    var d = Math.abs(date.getTime() - Date.now())/86400000;
    if (d <= 1.0) {
      // Show time instead of date
      return date.toLocaleTimeString();
    }
    return date.toLocaleDateString();
  });

  Handlebars.registerHelper('loop', function(count, block) {
    var data = '';
    for(var i = 0; i != count; ++i)
      data += block.fn(i);
    return data;
  });

  Handlebars.registerHelper('rebase', function(value, howmuch) {
    return value+howmuch;
  });

  Handlebars.registerHelper('lt', function(v1, v2, options) {
    if(v1 > v2) {
      return options.fn(this);
    }
    return options.inverse(this);
  });

  var menu = Handlebars.getTemplate('menu');
  $('#header').html(menu());

  section = getUrlParameter("section");
  switch (section) {
    case 'search':
      showSearch();
      break;
    case 'upload':
      showUpload();
      break;
    case 'categories':
      showCategories();
      break;
    case 'tags':
      showTags();
      break;
    case 'status':
      showStatus();
      break;
    case 'documents':
    default:
      var doc = getUrlParameter('view');
      if (doc)
        showDoc(doc);
      else
        showDocs();
      break;
  }

});

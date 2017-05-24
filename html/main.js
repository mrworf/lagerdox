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

  this.genericError = function(result) {
    alert("AJAX call failed!\nError:" + result['error']);
  }

  this.deleteDocument = function(id, resultFunction, errorFunction) {
    this.execServer('/document/' + id, resultFunction, errorFunction, 'DELETE');
  }

  this.addCategory = function(name, filter, resultFunction, errorFunction) {
    this.execServer('/category', resultFunction, errorFunction, 'PUT', {'name':name,'filter':filter});
  }

  this.deleteCategory = function(id, resultFunction, errorFunction) {
    this.execServer('/category', resultFunction, errorFunction, 'DELETE', {'id':id});
  }

  this.deleteTag = function(id, resultFunction, errorFunction) {
    this.execServer('/tag', resultFunction, errorFunction, 'DELETE', {'id':id});
  }

  this.addTag = function(name, resultFunction, errorFunction) {
    this.execServer('/tag', resultFunction, errorFunction, 'PUT', {'name':name});
  }
}

$( document ).ready(function() {
  client = new LagerDoxClient();

  function showDocs() {
    history.pushState(null, "upload", "?section=documents");
    $('#content').empty();
    client.getDocuments(function(obj) {
      var comp = Handlebars.getTemplate('document_list');
      $('#content').html(comp({'server' : 'magi.sfo.sensenet.nu', 'items' : obj['result']}));

      $('.document_item').on('click', '#item_delete', function(e) {
        deleteDoc(e.target.dataset.id, function() { $(e.delegateTarget).remove(); });
      });
    });
  }

  function deleteDoc(id, success) {
    if (confirm('Are you sure you want to delete this document? It cannot be undone!')) {
      client.deleteDocument(id, function(result) {
        if (success)
          success(result);
      });
    }
  }

  function deleteCategory(obj) {
    if (confirm('Are you sure you want to delete this category? It cannot be undone!')) {
      client.deleteCategory(obj['id'], function(result) {
        console.log('deleting the category from display, id = ' + obj['item']);
        $('#cat' + obj['item']).remove();
      });
    }
  }

  function deleteTag(obj) {
    if (confirm('Are you sure you want to delete this tag? It cannot be undone!')) {
      client.deleteTag(obj['id'], function(result) {
        console.log('deleting the tag from display, id = ' + obj['item']);
        $('#tag' + obj['item']).remove();
      });
    }
  }

  function showDoc(id) {
    history.pushState(null, "upload", "?section=documents&view=" + id);
    $('#content').empty();
    client.getDocument(id, function(obj) {
      var comp = Handlebars.getTemplate('document');
      obj['server'] = 'magi.sfo.sensenet.nu';
      $('#content').html(comp(obj));

      $('.document').on('click', '#item_delete', function(e) {
        deleteDoc(e.target.dataset.id, function() { showDocs(); });
      });
    }, function() {
      showDocs();
    });
  }

  function showTags() {
    history.pushState(null, "upload", "?section=tags");
    $('#content').empty();
    client.getTags(function(obj) {
      for (var d in obj["result"]) {
        tag = obj["result"][d];
        console.log(tag);

        var element = '<div id="tag' + d + '">';
        element += '<button id="del' + d + '">Delete</button>';
        element += tag['name'];
        element += '</div>';
        $('#content').append(element);
        $('#del'+d).bind('click', {'id':tag['id'], "item":d}, function(event) { deleteTag(event.data); });

      }
      element = '<input type="text" id="name"><button type="button" id="add">Add</button>';
      $('#content').append(element);
      $('#add').click(function() {
        var name = $('#name').val().trim();
        if (name == '')
          alert('Name field is empty, cannot add tag');
        else {
          client.addTag(name, function(result) {
            showTags();
          });
        }
      });
    });
  }

  function showStatus() {
    history.pushState(null, "upload", "?section=status");
    $('#content').empty();

    var comp = Handlebars.getTemplate('status');

    /**
      'overall' : 'INIT',
      'files' : 0,
      'pages' : 0,
      'file' : 0,
      'page' : 0,
      'sub' : ''
    */
    var element = '<span id="statusbox">'
    element += 'Status: <span id="status_overall"></span><br/>';
    element += 'Documents: <span id="status_pending"></span><br/>';
    element += '<hR>';
    element += 'Current document:<br>';
    element += 'Processing sub document <span id="status_file"></span> of <span id="status_files"></span><br/>';
    element += 'Processing page <span id="status_page"></span> of <span id="status_pages"></span><br/>';
    element += 'Current step: <span id="status_step"></span><br/>';
    '</span>';
    $('#content').html('<div class="status"></div>');
    refreshStatus(comp);
  }

  function refreshStatus(comp) {
    client.getStatus(function(obj) {
      if ($('.status').length) {
        $('#content').html(comp(obj));
        /*
        if ($.isEmptyObject(obj['jobs'])) {
          $('#status_pending').text('0');
          $('#status_overall').text('IDLE');
          $('#status_file').text('0');
          $('#status_files').text('0');
          $('#status_page').text('0');
          $('#status_pages').text('0');
          $('#status_step').text('');
        } else {
          // Find active one
          var c = 0;
          for (var k in obj['jobs']) {
            c++;
            if (obj['jobs'][k]['overall'] != 'PENDING') {
              $('#status_overall').text(obj['jobs'][k]['overall']);
              if (obj['jobs'][k]['files'] == 0) {
                $('#status_file').text('N/A');
                $('#status_files').text('N/A');
              } else {
                $('#status_file').text(obj['jobs'][k]['file']+1);
                $('#status_files').text(obj['jobs'][k]['files']);
              }
              $('#status_page').text(obj['jobs'][k]['page']+1);
              $('#status_pages').text(obj['jobs'][k]['pages']);
              $('#status_step').text(obj['jobs'][k]['sub']);
              break;
            }
          }
          $('#status_pending').text("" + c);
        }
        */
        setTimeout(function() { refreshStatus(comp); }, 1000);
      }
    });
  }

  function showCategories() {
    history.pushState(null, "upload", "?section=category");
    $('#content').empty();
    client.getCategories(function(obj) {
      var element = '';
      for (var d in obj["result"]) {
        cat = obj["result"][d];

        element  = '<div id="cat' + d + '">';
        element += '<button id="del' + d + '">Delete</button>';
        element += cat['name'];
        element += cat['filter'];
        element += '</div>';
        $('#content').append(element);
        $('#del'+d).bind('click', {'id': cat['id'], 'item':d}, function(event) { deleteCategory(event.data); });
      }
      element = '<input id="name" type="text"><input id="filter" type="text"><button type="button" id="add">Add category</button>';
      $('#content').append(element);
      $('#add').on('click', function() {
        if ($('#name').val().trim() == '')
          alert('No name provided');
        else
          client.addCategory($('#name').val(), JSON.stringify({'keywords':$('#filter').val().split(/\s+/)}), function(result) {
            showCategories();
          });
      });
    });
  }

  function showUpload() {
    history.pushState(null, "upload", "?section=upload");
    $('#content').empty();
    var element = '<span>File</span>';
    element += '<input type="file" id="file" name="file" data-url="http://magi.sfo.sensenet.nu:7000/upload" multiple/><br/>';
    element += '<div id="progress"><div class="bar" style="width: 0%;"></div></div>';

    $('#content').append(element);
    $('#file').fileupload({
      progressall: function (e, data) {
        var progress = parseInt(data.loaded / data.total * 100, 10);
        $('#progress .bar').css(
          'width',
          progress + '%'
        );
      },
      done: function (e, data) {
        showStatus();
        /*
        $.each(data.result.files, function (index, file) {
            $('#content').append(file.name);
        });
        */
      }
    });
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
    case '':
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

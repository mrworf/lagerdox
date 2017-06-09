$( document ).ready(function() {
  var serverName = "magi.sfo.sensenet.nu";
  var client = new LagerDoxClient('http://' + serverName + ':7000/');
  var maxperpage = 15;

  // See http://berzniz.com/post/24743062344/handling-handlebarsjs-like-a-pro
  Handlebars.getTemplate = function(name) {
    if (Handlebars.templates === undefined || Handlebars.templates[name] === undefined) {
      $.ajax({
        url : 'templates/' + name + '.html',
        success : function(data) {
          if (Handlebars.templates === undefined) {
              Handlebars.templates = {};
          }
          Handlebars.templates[name] = Handlebars.compile(data);
        },
        async : false
      });
    }
    return Handlebars.templates[name];
  };


  function showDocs() {
    $('#content').empty();
    showProgress('#content');

    client.getDocuments(function(obj) {
      var comp = Handlebars.getTemplate('document_list');

      // We may need to paginate this if the number of results are too large
      if (obj['result'].length > maxperpage) {
        var comp2 = Handlebars.getTemplate('paginator');
        var page = getUrlParameter("page");
        if (page == null)
          page = 1;
        else
          page = parseInt(page);

        count = Math.ceil(obj['result'].length/maxperpage);
        var subset = obj['result'].slice( (page-1)*maxperpage, page*maxperpage );
        var pages = []
        for (var i = 1; i <= count; ++i)
          if (i == page)
            pages.push({'page' : i, 'current' : true});
          else
            pages.push({'page' : i});
        var paginator = {'pages' : pages, 'section' : 'documents'};
        if (page != 1)
          paginator['prev'] = page-1;
        if (page != count)
          paginator['next'] = page+1;

        $('#content').html(comp({'server' : serverName, 'items' : subset}));
        $('.paginator').html(comp2(paginator));
      } else {
        $('#content').html(comp({'server' : serverName, 'items' : obj['result']}));
      }
      $('.document_item').on('click', '#item_delete', function(e) {
        deleteDoc(e.target.dataset.id, function() { $(e.delegateTarget).remove(); });
      });
      $('.document_item').on('click', '#item_download', function(e) {
        downloadDoc(e.target.dataset.id);
      });
      makeLinksSmarter();
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
    if (getUrlParameter('view') != id)
      history.pushState(null, "upload", "?section=documents&view=" + id);
    $('#content').empty();
    client.getDocument(id, function(obj) {
      obj = obj['result'];
      var comp = Handlebars.getTemplate('document');
      obj['server'] = serverName;
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
      makeLinksSmarter();
    }, function() {
      showDocs();
    });
  }

  function showTags() {
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
          showTags();
        } else {
          client.editTag($('#save').data('id'), $('#name').val(), function(result) {
            showTags();
          });
        }
      });
      makeLinksSmarter();
    });
  }


  function showStatus() {
    if ($('.status').length)
      return;
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
          var keys = data['keywords'];
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
          client.addCategory($('#name').val(), JSON.stringify({'keywords':$('#keywords').val()}), function(result) {
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
          client.editCategory($('#save').data('id'), $('#name').val(), JSON.stringify({'keywords':$('#keywords').val()}), function(result) {
            showCategories();
          });
        }
      });
      $('#test').on('click', function(e) {
        if ($('#keywords').val().trim() == '') {
          alert('No filter provided');
        } else {
          client.testFilter($('#keywords').val().trim(), function(result) {
            console.log(result);
          });
        }
      });
      makeLinksSmarter();
    });
  }

  function showUpload() {
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
    $('#content').empty();
    var comp = Handlebars.getTemplate('search');
    $('#content').html(comp());
    $('#query').val(q);
    search(q);

    $('#query').on('keypress', function(event) {
      if(event.keyCode == 13) { // 13 = Enter Key
        search_validate();
      }
    });

    $('#search').on('click', function() {
      search_validate();
    });
    makeLinksSmarter();
  }

  function search_validate() {
      if ($('#query').val().trim().length < 3) {
        alert('You need at least 3 characters to search for');
        return;
      }

      history.pushState(null, "search", "?section=search&q=" + encodeURIComponent($('#query').val()));
      search($('#query').val());
    }

  function search(query) {
    $('#results').empty();
    if (query != null) {
      query = query.trim();
      showProgress('#results');
      client.search(query, function(obj) {
        var comp = Handlebars.getTemplate('search_result');

        if (obj['result'].length > maxperpage) {
          var comp2 = Handlebars.getTemplate('paginator');
          var page = getUrlParameter("page");
          if (page == null)
            page = 1;
          else
            page = parseInt(page);

          count = Math.ceil(obj['result'].length/maxperpage);
          var subset = obj['result'].slice( (page-1)*maxperpage, page*maxperpage );
          var pages = []
          for (var i = 1; i <= count; ++i)
            if (i == page)
              pages.push({'page' : i, 'current' : true});
            else
              pages.push({'page' : i});
          var paginator = {'current' : page, 'pages' : pages, 'section' : 'search', 'extras' : '&q=' + encodeURIComponent(query)};
          if (page != 1)
            paginator['prev'] = page-1;
          if (page != count)
            paginator['next'] = page+1;

          $('#results').html(comp({'query' : query, 'server' : serverName, 'items' : subset}));
          $('.paginator').html(comp2(paginator));
        } else {
          $('#results').html(comp({'query' : query, 'server' : serverName, 'items' : obj['result']}));
        }
        makeLinksSmarter();
      });
    }
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

  /**
   * Places a temporary template into dest
   */
  function showProgress(dest) {
    var comp = Handlebars.getTemplate('progress');
    $(dest).html(comp());
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

  function processRequest() {
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
        if (section != 'documents')
          history.replaceState(null, '', '?section=documents');
        var doc = getUrlParameter('view');
        if (doc)
          showDoc(doc);
        else
          showDocs();
        break;
    }
  }

  function makeLinksSmarter() {
    $('a').off('click').on('click', function(obj) {
      history.pushState(null, '', $(obj.currentTarget).attr('href'));
      processRequest();
      return false;
    });
  }

  // Capture browser back/forward and evaluate URL
  $(window).on('popstate', function() {
    processRequest();
  });

  processRequest();

});

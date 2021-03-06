sc = sc || {};

sc.lzh2enLookup = {
    buttonId: "lzh2en",
    chineseClasses: "P, H1, H2, H3",
    active: false,
    dictRequested: false,
    chineseIdeographs: /[\u4E00-\u9FCC　。]/g, //CFK Unified Ideographs
    chinesePunctuation: /[　、。]/g,
    loading: false,
    queue: [],
    markupTarget: null,
    originalHTML: null,
    mouseIn: 0,
    currentLookup: null,
    lastCurrentLookup: null,
    init: function(button, markup_target){
        this.markupTarget = $(markup_target).addClass('lzh2enLookup')[0];
        this.button = $(button).on('click', sc.lzh2enLookup.toggle);
        if (sc.sessionState.getItem('lzh2en.active')) {
            this.activate();
        }
    },
    before: function(){
        self = sc.lzh2enLookup;
        sc.sidebar.messageBox.clear();        
        var message = '<p>Loading Chinese to English dictionary data, this may take some time (~1MB)</p>'
        sc.sidebar.messageBox.show(message, {id: 'lzh_msg_loading'});
    },
    done: function(){
        var self = sc.lzh2enLookup;
        sc.sidebar.messageBox.remove('lzh_msg_loading');
        var message = '<p>Chinese to English lookup activated.</p>\
            <p>Use the mouse or left, right arrow keys to navigate the text (shift-right to advance more).</p>\
            <p>A red border indicates modern usage, possibly unrelated to early Buddhist usage.</p>'
        sc.sidebar.messageBox.show(message);
        self.currentLookup = $('span.lookup:first')[0];
        self.lastCurrentLookup = self.currentLookup;
    },
    fail: function(jqXHR, textStatus, errorThrown){
        sc.sidebar.messageBox.remove('lzh_msg_loading');
        var msg = '<div>Failed to download dictionary data because of <em>{}</em></div>'.format(textStatus);
        sc.sidebar.messageBox.show(msg, {timeout: 10000});
    },
    activate: function(){
        var self = this;
        if (!this.originalHTML)
            this.originalHTML = this.markupTarget.innerHTML;
        
        if (!this.dictRequested && !window.sc.lzh2enData)
        {
            self.before();
            this.dictRequested = true;
            sc.lzh2enDataScripts.forEach(function(url, i){
                var jqXHR = jQuery.ajax({
                    url: sc.jsBaseUrl+url,
                    dataType: "script",                    
                    crossDomain: true,
                    cache: true,
                    timeout: 180 * 1000
                });
                if (i == 0) {
                    jqXHR.done(self.done);
                    jqXHR.fail(self.fail);
                }
            });
        }
        this.generateMarkup();
        $(document).on('mouseenter', 'span.lookup', function(){
            self.mouseIn ++;
        })
        $(document).on('mouseleave', 'span.lookup', function(){
            self.mouseIn --;
        })
        $(document).on('keyup', '', function(e){
            if (!self.mouseIn)
                return
            if (e.keyCode == 39 || e.keyCode == 37)
                e.preventDefault();
            if (e.keyCode == 39) {
                var from = self.currentLookup;
                if (self.lastCurrentLookup && e.shiftKey)
                    from = self.lastCurrentLookup;
                var next = nextInOrder(from, 'span.lookup:not(.punctuation)');
                if (!next)
                    return
                self.setCurrent(next)
            } else if (e.keyCode == 37){
                var prev = previousInOrder(self.currentLookup, 'span.lookup:not(.punctuation)');
                if (!prev)
                    return
                self.setCurrent(prev);
            }
        });
        sc.sessionState.setItem('lzh2en.active', true);
    },
    deactivate: function(){
        this.markupTarget.innerHTML = this.originalHTML;
        sc.sidebar.messageBox.clear();
        sc.sidebar.messageBox.show('<p>Lookup disabled.</p>', {'timeout': 5000});
        sc.sessionState.setItem('lzh2en.active', false);
    },
    generateMarkup: function() {
        if (this.button)
            this.button.attr('disabled', 'disabled');
        this.markupGenerator.start();
        $(document).on('mouseenter', 'span.lookup', sc.lzh2enLookup.lookupHandler);
    },
    markupGenerator: {
        //Applies markup incrementally to avoid a 'browser stall'
        start: function(){
            this.node = sc.lzh2enLookup.markupTarget;
            this.startTime = Date.now();
            this.step();
        },
        step: function(){
            for (var i = 0; i < 10; i++){
                if (this.node === undefined) {
                    this.andfinally();
                    return;
                }
                var nextNode = nextInOrderByType(this.node, document.TEXT_NODE)
                this.textNodeToMarkup(this.node);
                this.node = nextNode;
            }
            setTimeout('sc.lzh2enLookup.markupGenerator.step.call(sc.lzh2enLookup.markupGenerator)', 5);
        },
        andfinally: function(){
            self = sc.lzh2enLookup;
            if (self.button)
                self.button.removeAttr('disabled');
            
        },
        textNodeToMarkup: function(node) {
            if (node === undefined) return;
            var text = node.nodeValue;
            if (!text || text.search(sc.lzh2enLookup.chineseIdeographs) == -1){
                return
            }
            var proxy = document.createElement("span");
            node.parentNode.replaceChild(proxy, node);
            proxy.outerHTML = this.toLookupMarkup(text);
        },
        toLookupMarkup: function(input)
        {
            var self = sc.lzh2enLookup,
                chinesePunctuation = self.chinesePunctuation;
            
            return input.replace(self.chineseIdeographs, function(ideograph){
                var eclass = 'lookup';
                if (ideograph.match(chinesePunctuation))
                    eclass += ' punctuation';
                return '<span class="' + eclass +'">' + ideograph + '</span>'
            });
        }
    },
    toggle: function(){
        self = sc.lzh2enLookup;
        self.active = !self.active;
        if (self.active) self.activate()
        else self.deactivate();
    },
    setCurrent: function(node) {
        var self=this,
            graphs = '',
            nodes = $(),
            iter = new Iter(node),
            i
        $('.popup').remove()
        $('.current_lookup').removeClass('current_lookup fallback')
        this.currentLookup = node
        while (graphs.length < 10) {
            if ($(node).is('span.lookup')) {
                graphs += $(node).text();
                nodes.push(node)
            }
            node = nextInOrder(node, document.ELEMENT_NODE)
            if (!node) {
                break
            }
        }
        
        if (!graphs)
            return

        var popup = ['<div class="popup"><table>'],
            first = true,
            fallback = false;
        for (i = graphs.length; i > 0; i--) {
            var snip = graphs.slice(0, i)
            if (snip in sc.lzh2enData) {
                popup.push(self.lookupWord(snip))
                if (first) {
                    first = false;
                    nodes.slice(0, i).addClass('current_lookup')
                    this.lastCurrentLookup = nodes[i-1];
                }
            } else if (i == 1 && snip in sc.lzh2enFallbackData) {
                popup.push(self.lookupWord(snip))
                popup[0] = '<table class="popup fallback">'
                fallback = true
                if (first) {
                    first = false;
                    nodes.slice(0, i).addClass('current_lookup fallback')
                    this.lastCurrentLookup = nodes[i-1];
                }
            }
        }
        if (this.lastCurrentLookup == null)
            this.lastCurrentLookup = this.currentLookup;
        if (first)
            return

        popup.push('</table></div>')

        popup = self.popup(nodes[0], popup.join('\n'))
    },
    lookupHandler: function(e){
        sc.lzh2enLookup.setCurrent(e.target);
    },
    lookupWord: function(graph){
        //Check if word exists and return HTML which represents the meaning.
        var out = "";
        graph = graph.replace(/\u2060/, '');
        if (sc.lzh2enData[graph])
        {
            var href = "http://www.buddhism-dict.net/cgi-bin/xpr-ddb.pl?q=" + encodeURI(graph);
            return ('<tr><td class="ideograph"><a href="' + href + '">' + graph + '</a></td> <td class="meaning"> ' + sc.lzh2enData[graph][0] + ': ' + sc.lzh2enData[graph][1] + '</td></tr>');
        } else if (sc.lzh2enFallbackData[graph]) {
            return ('<tr class="fallback"><td class="ideograph"><a>' + graph + '</a></td> <td class="meaning"> ' + sc.lzh2enFallbackData[graph][0] + ': ' + sc.lzh2enFallbackData[graph][1] + '</td></tr>')
        }
        return "";
    },
    popup: function(parent, popup) {
        var offset, docWith, dupe, docWidth, isAbsolute = false
        if ('left' in parent || 'top' in parent) {
            offset = parent
            offset.left = offset.left || 0
            offset.top = offset.top || 0
            parent = document.body
            isAbsolute = true

        } else {
            parent = $(parent)
            offset = parent.offset()
        }
        popup = $(popup)

        //We need to measure the doc width now.
        docWidth = $(document).width()
        // We need to create a dupe to measure it.
        dupe = $(popup).clone()
            
        $(this.markupTarget).append(dupe)
        var popupWidth = dupe.innerWidth(),
            popupHeight = dupe.innerHeight();
        dupe.remove()
        //The reason for the duplicity is because if you realize the
        //actual popup and measure that, then any transition effects
        //cause it to zip from it's original position...
        if (!isAbsolute) {
            offset.top += parent.innerHeight() - popupHeight - parent.outerHeight();
            offset.left -= popupWidth / 2;
        }

        if (offset.left < 1) {
            offset.left = 1;
            popup.innerWidth(popupWidth + 5);
        }
        
        if (offset.left + popupWidth + 5 > docWidth)
        {
            offset.left = docWidth - (popupWidth + 5);
        }
        popup.offset(offset)
        $(this.markupTarget).append(popup)
        popup.offset(offset)

        popup.mouseleave(function(e){$(this).remove()});
        
        return popup;
    }
}

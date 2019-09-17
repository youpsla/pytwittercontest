function initViewer(ref, table) {
    //var ws = new WebSocket("ws://localhost:8888/ws/?ref="+ref);
    // ws.onopen = function(evt) {
    //     console.log("Connected!");
    // };
    console.log('initviewer');

    console.log(ref);
    // constructor
    var Enaml = (function () {
        function Enaml() {
            console.log('enaml function launched');
            this.ws = null;
            this.connect();
            this.observe();
        };

        Enaml.prototype.observe = function () {
            var Enaml = this;

            $('#full_table tbody').on('click', 'tr', function (e) {
                e.preventDefault();
                data = table.row(this).data();
                userid = data['id'];
                Enaml.sendEvent({ 'userid': data['id'], 'event': 'user_tweets' });
            });

            $('#update_summary_report').on('click', function (e) {
                e.preventDefault();
                console.log('Event send: update_summary_report')
                Enaml.sendEvent({ 'event': 'update_summary_report' });
            });

        };

        Enaml.prototype.unobserve = function () {
            var Enaml = this;
            $('[data-onclick="1"]').off('click');
        };

        // Define Enaml
        Enaml.prototype.onOpen = function (event) {
            console.log("On open!");
        };

        Enaml.prototype.onMessage = function (event) {
            var change = JSON.parse(event.data);
            var $tag = $('[ref="' + change.ref + '"]');
            if (change.type === "refresh") {
                this.unobserve();
                $tag.html(change.value);
                this.observe();
            } else if (change.type === "trigger") {
                $tag.trigger(change.value);
            } else if (change.type === "added") {
                $tag.append(change.value);
            } else if (change.type === "removed") {
                $tag.find('[ref="' + change.value + '"]').remove();
            } else if (change.type === "update") {
                if (change.name === "text") {
                    var node = $tag.contents().get(0);
                    if (!node) {
                        node = document.createTextNode("");
                        $tag.append(node);
                    }
                    node.nodeValue = change.value;
                    // TODO: handle tail
                } else if (change.name === "attrs") {
                    $.map(change.value, function (v, k) {
                        $tag.prop(k, v);
                    });
                } else {
                    $tag.prop(change.name, change.value);
                }
                // Special hack for materialize...
                if ($tag.prop('tagName') === 'SELECT') {
                    $tag.material_select();
                }
            }
        };

        Enaml.prototype.connect = function () {
            var Enaml = this;
            // var url = "ws://"+window.location.host+window.location.pathname+"ws";
            var url = "ws://localhost:8888/ws?ref=" + ref
            console.log("Connecting to " + url);
            this.ws = new WebSocket(url);
            this.ws.onopen = function (e) {
                Enaml.onOpen(e);
            };
            this.ws.onmessage = function (e) {
                Enaml.onMessage(e);
            };
            this.ws.onclose = function (e) {
                Enaml.onClose(e);
            };
        };

        Enaml.prototype.sendEvent = function (event) {
            event.viewer_ref = $('html').attr('ref');
            console.log('Event');
            console.log(event);
            this.ws.send(JSON.stringify(event));
        };

        Enaml.prototype.onClose = function (event) {
            console.log("Connection is closed...");
            this.connect();
        };
        
        return Enaml;
    })();

    window.Enaml = new Enaml();

    console.log(window.Enaml);


};



$(function() {
    var need_request = true;
    var lampSwitchers = {};
    var socket;
    var log = function(msg){};

    /* Объект запроса на сервер */
    function Request(){
        this.updateAll = function(data) {
            for (var i=0;i<data.length;i++) {
                if (data[i].object_type == 'lamp') {
                    var lamp = data[i],
                        switcher = lampSwitchers[lamp.id];
                    if (switcher) {
                        switcher.switchByStatus(lamp.on);
                        if (lamp.dimmable) {
                            switcher.setValue(lamp.level);
                        }
                    }
                };
                if (data[i].object_type == 'sensor') {
                    var sensor = data[i];
                    $('#sensor-'+sensor.id).find('div.panel-body .sensor-value').html(sensor.value);
                }
                if (data[i].object_type == 'node') {
                    var node = data[i];
                    log(node);
                    if (node.online) {
                        var last_answer_time = new Date(node.last_answer_time),
                            last_answer_text = global_settings.last_answer_time_prefix
                                + last_answer_time.getFullYear() + "-"
                                + (last_answer_time.getMonth() < 10 ? '0' : '')
                                + (last_answer_time.getMonth() + 1) + "-"
                                + (last_answer_time.getDate() < 10 ? '0' : '')
                                + last_answer_time.getDate() + " "
                                + (last_answer_time.getHours() < 10 ? '0' : '')
                                + last_answer_time.getHours() + ":"
                                + (last_answer_time.getMinutes() < 10 ? '0' : '')
                                + last_answer_time.getMinutes() + ":"
                                + (last_answer_time.getSeconds() < 10 ? '0' : '')
                                + last_answer_time.getSeconds();
                        console.log(last_answer_time);
                        $('[data-node-id='+node.id+']').addClass("online");
                        $('[data-node-id='+node.id+']').attr("title", last_answer_text);
                        $('.node_last_answer_time').html(last_answer_text);
                    } else {
                        $('[data-node-id='+node.id+']').removeClass("online");
                        $('[data-node-id='+node.id+']').attr("title", last_answer_text);
                        $('.node_last_answer_time').html(last_answer_text);
                    }
                }
            }
        }
        this.process = function(data) {
            try {
                socket.send(JSON.stringify(data));
            } catch (err) {
                socket.close();
                return;
            }
        }
    }

    /* Объект выключателя ламп */
    function LampSwitcher(id){
        this.id = id;
        this.switcher = $("#lamp-" + this.id + " input[data-toggle=toggle]");
        this.slider = $("#lamp-" + this.id + " .dimmer");
        this.value = 0;
        var sliderInUse = false;

        this.changeSwitcherStatus = function (){
            var data = [{"id": id, "object_type": "lamp", "on": $(this).prop('checked')}],
                request = new Request();

            request.process(data);
        }
        this.switcher.on('change', this.changeSwitcherStatus);

        /* Slider */
        this.changeSliderValue = function(slideEvt) {
            var data = [{"id": id, "object_type": "lamp", "level": slideEvt.value.newValue}],
                request = new Request();

            request.process(data);
        }
        this.slider.slider({
            formatter: function(value) {
                return value + '%';
            }
        });
        this.slider.on('change', this.changeSliderValue);
        this.slider.on('slideStart', function(){sliderInUse = true; log("sliderInUse true")});
        this.slider.on('slideStop', function(){sliderInUse = false; log("sliderInUse false")});
        /* End Slider */

        this.switchOn = function (){
            if (!this.switcher.length) return;
            this.switcher.off( "change" );
            this.switcher.bootstrapToggle('on');
            this.switcher.on('change', this.changeSwitcherStatus);
            $('#lamp-'+this.id).find('.panel').removeClass('panel-default').removeClass('panel-danger').addClass('panel-primary');
        };
        this.switchOff = function(){
            if (!this.switcher.length) return;
            this.switcher.off( "change" );
            this.switcher.bootstrapToggle('off');
            this.switcher.on('change', this.changeSwitcherStatus);
            $('#lamp-'+this.id).find('.panel').removeClass('panel-primary').removeClass('panel-danger').addClass('panel-default');
        };
        this.switchError = function(){
            if (!this.switcher.length) return;
            this.switcher.off( "change" );
            this.switcher.bootstrapToggle('off');
            this.switcher.on('change', this.changeSwitcherStatus);
            $('#lamp-'+this.id).find('.panel').removeClass('panel-default').removeClass('panel-primary').addClass('panel-danger');
        };
        this.switchByStatus = function(status){
            if (!this.switcher.length) return;
            if (status === true) {
                this.switchOn();
            } else if (status === false) {
                this.switchOff();
            } else {
                this.switchError();
            }
        };
        this.setValue = function (value){
            log(sliderInUse);
            if (!sliderInUse) {
                this.value = value;
                log(this.slider);
                this.slider.slider('setValue', value);
            }
        };
    }


    /* Инициализация переключателей ламп */
    $("div[id^='lamp-']").each(function(index, obj){
        var id = obj.id.split('-')[1]*1;
        lampSwitchers[id] = new LampSwitcher(id);
    });

    /* Переключалка всей зоны */
    $(".zone-lamps-switcher").click(function(){
        var id = $(this).attr('data-zone-id')*1,
            status = $(this).attr('data-status'),
            data = [{"id": id, "object_type": "zone_lamps", "on": status=="true"}],
            request = new Request();
        request.process(data);
    });

    /* Переключалка всей зоны */
    $(".all-lamps-switcher").click(function(){
        var status = $(this).attr('data-status'),
            data = [{"object_type": "all_lamps", "on": status=="true"}],
            request = new Request();
        request.process(data);
    });

    /* End Autoupdate */
    var charts = {};
    $(".morris-area-chart").each(function(index){
        var obj = $(this),
            url = obj.attr('data-url');
        $.get(url, function( data ) {
            charts[obj.attr('id')] = Morris.Area({
                element: obj.attr('id'),
                yLabelFormat: function (y) { return Math.round(y*100)/100; },
                data: data,
                xkey: 'time',
                ykeys: ['max', 'avg', 'min'],
                labels: ['Max', 'Avg', 'Min'],
                lineColors: ['blue', 'red', 'green'],
                fillOpacity: 0.7,
                pointSize: 2,
                hideHover: 'auto',
                behaveLikeLine: true,
                ymin: 'auto',
                ymax: 'auto',
                resize: true
            });
        });
    });
    var updateMorris = function(){
        $(".morris-area-chart").each(function(index){
            var obj = $(this),
                url = obj.attr('data-url');
            $.get(url, function( data ) {
                charts[obj.attr('id')].setData(data);
                charts[obj.attr('id')].redraw();
            });
        });
    }
    //setInterval(updateMorris, 10000);

    /*Socket*/
    if (!("WebSocket" in window)) {
        alert("Your browser does not support web sockets");
    }else{
        setup();
    }

    function setup(){

        var host = global_settings.socket_url;
        socket = new ReconnectingWebSocket(host);

        // event handlers for websocket
        if(socket){

            socket.onopen = function(){
            }

            socket.onmessage = function(msg){
                var request = new Request();
                showServerResponse(msg.data);
                request.updateAll(JSON.parse(msg.data))
            }

            socket.onclose = function(event){
              if (event.wasClean) {
                showServerResponse("The connection has been closed clean.");
              } else {
                showServerResponse('Обрыв соединения');
              }
              showServerResponse('Код: ' + event.code + ' причина: ' + event.reason);
              showServerResponse(event);
              //setTimeout(function(){setup()}, 5000);
            }
        }else{
            showServerResponse("invalid socket");
        }

        function showServerResponse(txt){
            log(txt);
        }
    };
    if (global_settings.debug) {
        log = function(msg){
            console.log(msg);
        }
    }
});

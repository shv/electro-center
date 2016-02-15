$(function() {
    var need_request = true;
    function LampSwitcher(id){
        this.id = id;
        this.switcher = $("#lamp-" + this.id + " input[data-toggle=toggle]");
        this.switchOn = function (){
            if (!this.switcher.length) return;
            this.switcher.bootstrapToggle('on');
            $('#lamp-'+this.id).find('.panel').removeClass('panel-default').removeClass('panel-danger').addClass('panel-primary');
        };
        this.switchOff = function(){
            if (!this.switcher.length) return;
            this.switcher.bootstrapToggle('off');
            $('#lamp-'+this.id).find('.panel').removeClass('panel-primary').removeClass('panel-danger').addClass('panel-default');
        };
        this.switchError = function(){
            if (!this.switcher.length) return;
            this.switcher.bootstrapToggle('off');
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
    }

    $(".zone-switcher").click(function(){
        var url = $(this).attr('data-url');
        need_request = false;
        $.get(url, function( data ) {
            for (var i=0;i<data.length;i++) {
                var lamp = data[i],
                    switcher = new LampSwitcher(lamp.id);

                switcher.switchByStatus(lamp.on);
            }
            need_request = true;
        })
    });

    $("input[data-toggle=toggle]").change(function(event){
        var obj = this,
            state = $(obj).prop('checked'),
            url = $(obj).attr('data-'+(state?'url-on':'url-off'));

        if (need_request) {
            need_request = false;
            $.get(url, function( data ) {
                for (var i=0;i<data.length;i++) {
                    var lamp = data[i],
                        switcher = new LampSwitcher(lamp.id);

                    switcher.switchByStatus(lamp.on);
                }
                need_request = true;
            })
        }
    });

    $(".morris-area-chart").each(function(index){
        var obj = $(this),
            url = obj.attr('data-url');
        $.get(url, function( data ) {
            Morris.Area({
                element: obj.attr('id'),
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

});

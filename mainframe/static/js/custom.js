$(function() {
    var need_request = true;

    $(".zone-switcher").click(function(){
        var url = $(this).attr('data-url');
        need_request = false;
        $.get(url, function( data ) {
            for (var i=0;i<data.length;i++) {
                var lamp = data[i],
                    switcher = $("#lamp-" + lamp["id"] + " input[data-toggle=toggle]");
                switcher.bootstrapToggle(lamp["on"]?'on':'off');

                if (lamp.on === true) {
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-default').removeClass('panel-danger').addClass('panel-primary');
                } else if (lamp.on === false) {
                    switcher.bootstrapToggle('off');
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-primary').removeClass('panel-danger').addClass('panel-default');
                } else {
                    switcher.bootstrapToggle('off');
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-default').removeClass('panel-primary').addClass('panel-danger');
                }
            }
            need_request = true;
        })
    });

    $("input[data-toggle=toggle]").change(function(event){
        var obj = this,
            state = $(obj).prop('checked'),
            url = $(obj).attr('data-'+(state?'url-on':'url-off'));

        if (need_request) {
            $.get(url, function( data ) {
                need_request = false;
                var lamp = data[0];
                if (lamp.on === true) {
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-default').removeClass('panel-danger').addClass('panel-primary');
                } else if (lamp.on === false) {
                    $(obj).bootstrapToggle('off');
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-primary').removeClass('panel-danger').addClass('panel-default');
                } else {
                    $(obj).bootstrapToggle('off');
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-default').removeClass('panel-primary').addClass('panel-danger');
                }
                need_request = true;
            })
        }
    });

});

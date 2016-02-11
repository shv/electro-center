$(function() {
    $(".lamp-switcher").bootstrapSwitch({
        onSwitchChange: function(event, state){
            var url = $(this).attr('data-'+(state?'on':'off')),
                obj = this;
            $.get(url, function( data ) {
                var lamp = data[0];
                if (lamp.on === true) {
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-default').removeClass('panel-danger').addClass('panel-primary');
                } else if (lamp.on === false) {
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-primary').removeClass('panel-danger').addClass('panel-default');
                } else {
                    $('#lamp-'+lamp.id).find('.panel').removeClass('panel-default').removeClass('panel-primary').addClass('panel-danger');
                }
            })
        }
    }).show();
    $(".zone-switcher").click(function(){
        var url = $(this).attr('data-url');
        $.get(url, function( data ) {
            // $("#lamp-5 .lamp-switcher").bootstrapSwitch("toggleState");
            // alert($("#lamp-5 .lamp-switcher").bootstrapSwitch("state"));
            location.reload();
        })
    });
});

$(document).ready(function(){
     $(".oculto").hide();
    $("#mi-boton").click(function(){
       

        $("#parrafo-principal")
            .text("¡El texto ha sido cambiado con jQuery!");
        $(".oculto").show();

    });
});
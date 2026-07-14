// ============================================================
// script.js - Login and registration form handling
//
// This file is shared between index.html (login) and
// registro.html (registration). Each page only has one form,
// so the handlers only run when the element exists.
//
// jQuery internally checks if the selected element exists
// before binding the event. If the element is not on the page
// (for example, #formulario-registro does not exist in index.html),
// it simply does nothing. It does not cause errors.
//
// This file handles:
// 1. Capturing the login form submission
// 2. Capturing the registration form submission
// 3. Sending data to the server via Ajax (jQuery)
// 4. Storing the JWT token and user name in sessionStorage
// 5. Redirecting to the dashboard on successful login
// 6. Redirecting to login on successful registration
// ============================================================

// API_URL defines the base address of the API.
// If the frontend and backend run on the same origin (same host and port),
// it can be an empty string "". If they are on different servers,
// put the full backend URL here.
// Example: "http://127.0.0.1:5000" or "https://mydomain.com/api"
var API_URL = "http://127.0.0.1:5000";

// $(document).ready() is a jQuery event that fires when
// all HTML content has finished loading. Without this, our
// script might try to find elements that don't exist on the page yet.
$(document).ready(function () {

    // ============================================================
    // LOGIN FORM
    // ============================================================
    // We capture the "submit" event of the form with id="formulario-login".
    // This event fires every time the user presses the "Log in" button
    // or presses Enter while inside a form field.
    // The "evento" parameter is the event object, which contains information
    // about what just happened.
    $("#formulario-login").on("submit", function (evento) {

        // preventDefault() stops the default form behavior,
        // which would reload the entire page. We want to send the
        // data via Ajax and handle the response without reloading.
        evento.preventDefault();

        // .val() gets the text the user typed in each field.
        // #correo and #password are the ids of the inputs in index.html.
        var correo = $("#correo").val();
        var password = $("#password").val();

        // Before sending a new request, we clear any previous
        // message that might be visible in the #mensaje-resultado div.
        // d-none hides the div, and we remove the color style classes.
        $("#mensaje-resultado")
            .addClass("d-none")
            .removeClass("alerta-exito alerta-error")
            .text("");

        // $.ajax() is jQuery's function for making HTTP requests.
        // It is similar to native JavaScript fetch(), but with different
        // syntax and better compatibility with older browsers.
        $.ajax({
            // url: where to send the request. We use API_URL + "/login"
            // so that if the server address ever changes, we only
            // need to change one line instead of searching the whole file.
            url: API_URL + "/login",

            // method: the HTTP verb. POST is used to send data to the server,
            // in this case the user's credentials.
            method: "POST",

            // contentType: tells the server what format the data is in.
            // "application/json" means the request body is JSON.
            contentType: "application/json",

            // data: the data we send. JSON.stringify() converts a normal
            // JavaScript object into a JSON text string, which is what
            // the server expects to receive.
            data: JSON.stringify({
                correo: correo,
                password: password
            }),

            // success only runs if the server responded with a
            // 2xx status code (200, 201, etc.), meaning everything went well.
            success: function (respuesta) {

                // We show a success message to the user.
                // We remove d-none to show the div, and add alerta-exito
                // so it appears in green.
                $("#mensaje-resultado")
                    .removeClass("d-none alerta-error")
                    .addClass("alerta-exito")
                    .text("Welcome, " + respuesta.nombre);

                // We store the JWT token and user name in sessionStorage.
                // sessionStorage is a browser storage that keeps
                // data while the browser tab is open.
                // If the user closes the tab, the data is automatically deleted.
                // This is different from localStorage, which keeps data
                // even after closing the browser.
                sessionStorage.setItem("tokenSesion", respuesta.token);
                sessionStorage.setItem("nombreUsuario", respuesta.nombre);

                // We redirect to the dashboard after 1.2 seconds (1200 milliseconds).
                // setTimeout creates a delay before executing the redirect.
                // We leave some time so the user can see the success
                // message before being redirected.
                setTimeout(function () {
                    window.location.href = "dashboard.html";
                }, 1200);
            },

            // error runs if the server responded with a 4xx or 5xx code,
            // meaning there was a problem (incorrect credentials, server
            // error, etc.).
            error: function (peticion) {

                // We start with a generic error message in case the server
                // response doesn't have a specific "error" field.
                var mensajeError = "An error occurred while logging in";

                // Status 429 = Too Many Requests. This means the account
                // is temporarily blocked due to too many failed login attempts.
                // We show a specific message with the remaining lockout time.
                if (peticion.status === 429) {
                    var retrySeconds = peticion.responseJSON.retry_after_seconds;
                    var minutes = Math.floor(retrySeconds / 60);
                    var seconds = retrySeconds % 60;
                    mensajeError = "Account temporarily locked. Try again in " +
                        minutes + "m " + seconds + "s";
                }

                // peticion.responseJSON contains the server's response
                // already parsed as a JavaScript object. If it exists and has
                // an "error" field, we use that message instead of the generic one.
                // This allows the backend to send messages like
                // "Incorrect email or password" directly.
                else if (peticion.responseJSON && peticion.responseJSON.error) {
                    mensajeError = peticion.responseJSON.error;
                }

                // We show the error message to the user in red.
                $("#mensaje-resultado")
                    .removeClass("d-none alerta-exito")
                    .addClass("alerta-error")
                    .text(mensajeError);
            }
        });
    });

    // ============================================================
    // REGISTRATION FORM
    // ============================================================
    // This block handles the account creation form submission.
    // It is similar to the login, but with two key differences:
    // 1. It sends 3 fields (nombre, correo, password) instead of 2
    // 2. It validates that both passwords match BEFORE sending
    // 3. It sends to /registro (public route) instead of /login

    $("#formulario-registro").on("submit", function (evento) {
        // We prevent the form from reloading the page
        evento.preventDefault();

        // We read the values of the 4 registration form fields.
        // Each id corresponds to an input in registro.html.
        var nombre = $("#registro-nombre").val();
        var correo = $("#registro-correo").val();
        var password = $("#registro-password").val();
        var password2 = $("#registro-password2").val();

        // We clear previous messages from the registration area.
        // Note: we use #mensaje-registro instead of #mensaje-resultado,
        // because each page has its own message div.
        $("#mensaje-registro")
            .addClass("d-none")
            .removeClass("alerta-exito alerta-error")
            .text("");

        // Client-side validation: passwords must match.
        // This avoids sending a request to the server that we know
        // will fail. The server also validates, but this quick check
        // gives immediate feedback to the user.
        if (password !== password2) {
            $("#mensaje-registro")
                .removeClass("d-none")
                .addClass("alerta-error")
                .text("Passwords do not match");
            return;
        }

        // Additional validation: the password must be at least
        // 6 characters long. Although the input already has minlength="6"
        // in HTML, some browsers don't enforce it, so it's better
        // to also verify it in JavaScript.
        if (password.length < 6) {
            $("#mensaje-registro")
                .removeClass("d-none")
                .addClass("alerta-error")
                .text("Password must be at least 6 characters long");
            return;
        }

        // We send the data to the server via Ajax.
        // The endpoint is /registro, which is a PUBLIC route (no
        // token required). The server will create the user and return
        // a 201 (Created) code if everything goes well.
        $.ajax({
            url: API_URL + "/registro",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                nombre: nombre,
                correo: correo,
                password: password
            }),

            // If the server responds with 201 (Created), the user
            // was created successfully.
            success: function (respuesta) {
                // We show a success message to the user
                $("#mensaje-registro")
                    .removeClass("d-none alerta-error")
                    .addClass("alerta-exito")
                    .text("Account created successfully. You can now log in.");

                // We clear the form fields so the user doesn't have
                // to delete what they typed.
                $("#formulario-registro")[0].reset();

                // After 2 seconds, we redirect to the login page
                // so the user can log in with their new account.
                setTimeout(function () {
                    window.location.href = "index.html";
                }, 2000);
            },

            // If the server responds with an error (400, 409, etc.)
            error: function (peticion) {
                var mensajeError = "An error occurred while creating the account";

                // If the server sent a specific error message,
                // we show it instead of the generic one.
                if (peticion.responseJSON && peticion.responseJSON.error) {
                    mensajeError = peticion.responseJSON.error;
                }

                $("#mensaje-registro")
                    .removeClass("d-none alerta-exito")
                    .addClass("alerta-error")
                    .text(mensajeError);
            }
        });
    });
});

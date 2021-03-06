/**
 * Common handlebar utility helpers.
 */


/**
 * Commafies large numbers.
 */
Handlebars.registerHelper("commafy", function(num) {
    return (num || 0).toString().replace(/(\d)(?=(\d{3})+(\.\d+)*$)/g, "$1,");
});

/**
 * Turns a decimal value into a whole (rounded) percent.
 */
Handlebars.registerHelper("percentify", function(num, options) {
    var value = num * 100;
    var decimals = options.hash.decimals || 0;
    return value.toFixed(decimals) + "%";
});

/**
 * Formats a number to a fixed number of decimal places.
 */
Handlebars.registerHelper("fixedPlaces", function(num, options) {
    return Number(num).toFixed(options.hash.digits || 0);
});

/**
 * Substring given start and len.
 */
Handlebars.registerHelper("substr", function(str, options) {
    var argsMap = options.hash;
    var len = argsMap.len === undefined ? str.length : argsMap.len;
    var start = argsMap.start === undefined ? 0 : argsMap.start;
    return String(str).substr(start, len);
});

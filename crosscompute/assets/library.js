(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
function define_get_adjective(adjectives, noun) {
  var adjective_expression_string = adjectives.join('|');
  var key_expression_string = '(' + adjective_expression_string + ')_' + noun;
  var key_expression = RegExp(key_expression_string.replace(/[-_]/g, '[-_]'));

  function get_adjective(key) {
    try {
      var adjective = key_expression.exec(key)[1];
    } catch(e) {
      var adjective = adjectives[0];
    }
    if (adjective_string.indexOf('-') > -1) {
      adjective = adjective.replace('_', '-');
    }
    return adjective;
  }

  return get_adjective;
}

module.exports.define_get_adjective = define_get_adjective;

},{}]},{},[1]);

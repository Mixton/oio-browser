var app = angular.module("oioBrowser");

app.filter('filesize', function() {
	return function(input) {
		if(!input) return "0 bytes"
    var current = -1;
    var units = ['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'];
    while (current++ < units.length -1) {
        number = Math.floor(input/(Math.pow(1024, current)));
        if (number == 0) {
          return Math.floor(input/(Math.pow(1024, current - 1))).toString() + " " + units[current - 1];
        }
    }
    return "OVERFLOW ERROR";
  }
});

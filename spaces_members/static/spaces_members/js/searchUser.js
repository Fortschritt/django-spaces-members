document.addEventListener("DOMContentLoaded", function(event) { 

var inputSelector = '#searchUser';
var formSelector = inputSelector+'Form';
var dropDownSelector = formSelector + ' .dropdown';
var dropDownMenuSelector = inputSelector+'Menu'


var url = $(formSelector).attr('action').slice(0,-2);

var getUsers = function() {
	var keyword = $(inputSelector).val();
	if (keyword) {
		$.ajax({
    	    type: 'GET',
        	url: url + keyword + '/',
            success : displayUsers
        })
	}
}

var addUserSuccess = function(data,respType,response) {
	location.reload();
}

var addUser = function(ev) {
	var userPK = $(ev.target.parentElement).attr('data-user-pk');
	var token = $(formSelector+' input[name="csrfmiddlewaretoken"]').val();
	var url = $(dropDownMenuSelector).attr('data-adduser-url');
	$.ajax({
		url: url,
        dataType:"json",
        type:"POST",
        data:{
	            user_pk: userPK,
   				csrfmiddlewaretoken:token,
            },
            success: addUserSuccess,

        });     
	return false;
}


var displayUsers = function(data, respType, response) {
	var users = JSON.parse(data.users);
	var content = '<ul class="media-list media-list-users list-group">';
	var len = users.length;
	// first create the list and add it to the DOM
	for (var i=0;i<len;i++) {
		var data = 'data-user-pk="' + users[i].pk + '"';
		content += '<li class="list-group-item">  <div class="media">' +
					   '<a class="media-left" href="#" '+data+'>'+
						   '<img class="media-object img-circle" src="'+
							users[i].avatar + '"></a>' +
					   '<div class="media-body">'+
						   '<a class="" href="#" '+data+'><strong>' + users[i].username + '</strong></a>'+
					   '</div></div></li>';
	}
	if (len==0) {
		content += '<li class="list-group-item">  <div class="media">' +
						'<div class="media-body">'+
						'<span class="icon icon-block"></span"'+
				   '</div></div></li>';
	}
	content += '</ul>'
	$(dropDownMenuSelector).html(content);
	// new elements in DOM, now add events
	$(dropDownMenuSelector).find('a').on('click', addUser)
}

$(inputSelector).on('keyup', getUsers);
$(formSelector).on('submit', function() {
	return false;
});

});
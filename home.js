/* Lightweight interactions for BidBell's editorial site. No tracking. */
(function(){
  var days=document.getElementById('days'),marks={30:'Marion, VA',31:'2 in CA'};
  if(days){
    ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(function(day){var cell=document.createElement('div');cell.className='dow';cell.textContent=day;days.appendChild(cell);});
    for(var blank=0;blank<5;blank++)days.appendChild(document.createElement('div'));
    for(var date=1;date<=31;date++){var cell=document.createElement('div');cell.textContent=date;if(marks[date]){cell.className='mark';var note=document.createElement('em');note.textContent=marks[date];cell.appendChild(note);}days.appendChild(cell);}
  }
  var amount=document.getElementById('amt'),saving=document.getElementById('save');
  document.querySelectorAll('.toggle button').forEach(function(button){button.addEventListener('click',function(){
    document.querySelectorAll('.toggle button').forEach(function(other){other.setAttribute('aria-pressed',String(other===button));});
    var yearly=button.getAttribute('data-p')==='y';amount.textContent=yearly?'$390':'$39';var period=document.createElement('small');period.textContent=yearly?'/year':'/month';amount.appendChild(period);saving.textContent=yearly?'Two months free, $78 less than paying monthly.':'';
  });});
})();

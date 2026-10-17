
(function(){
  document.documentElement.classList.add('js');
    // January 2027 calendar: starts on a Friday
  var days=document.getElementById('days'), marks={30:'Marion, VA',31:'2 in CA'};
  ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(function(d){var e=document.createElement('div');e.className='dow';e.textContent=d;days.appendChild(e);});
  for(var b=0;b<5;b++){var e=document.createElement('div');e.className='blank';days.appendChild(e);}
  for(var i=1;i<=31;i++){var c=document.createElement('div');c.textContent=i;
    if(marks[i]){c.className='mark';var em=document.createElement('em');em.textContent=marks[i];c.appendChild(em);c.appendChild(document.createElement('i'));}
    days.appendChild(c);}
  var tail=(5+31)%7; if(tail){for(var t=tail;t<7;t++){var x=document.createElement('div');x.className='blank';days.appendChild(x);}}
  // price toggle
  var amt=document.getElementById('amt'), save=document.getElementById('save');
  document.querySelectorAll('.toggle button').forEach(function(btn){btn.addEventListener('click',function(){
    document.querySelectorAll('.toggle button').forEach(function(o){o.setAttribute('aria-pressed',String(o===btn));});
    var y=btn.getAttribute('data-p')==='y';
    amt.innerHTML=y?'$390<small>/year</small>':'$39<small>/month</small>';
    save.textContent=y?'Two months free, $78 less than paying monthly.':'';
  });});
  // motion: the email arrives once; the sort runs when it scrolls into view; photos settle
  var mail=document.getElementById('mail'), sorter=document.getElementById('sorter');
  requestAnimationFrame(function(){setTimeout(function(){mail.classList.add('arrived');},250);});
  if(!('IntersectionObserver' in window)){sorter.classList.add('done');document.querySelectorAll('.photo.settle').forEach(function(p){p.classList.add('seen');});return;}
  var io=new IntersectionObserver(function(es){es.forEach(function(e){
    if(!e.isIntersecting) return;
    if(e.target===sorter){setTimeout(function(){sorter.classList.add('done');},500);} else {e.target.classList.add('seen');}
    io.unobserve(e.target);
  });},{threshold:.35});
  io.observe(sorter); document.querySelectorAll('.photo.settle').forEach(function(p){io.observe(p);});
  document.getElementById('replay').addEventListener('click',function(){sorter.classList.remove('done');setTimeout(function(){sorter.classList.add('done');},700);});
})();

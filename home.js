
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
  // the clock turns 5:58, 5:59, 6:00 ... 6:05, then the email lands (reduced motion: shown at 6:05 at once)
  document.querySelector('.hero').classList.add('dawn');
  var clk=document.getElementById('clk'), still=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(still||!clk){mail.classList.add('arrived');}
  else{var times=['5:58','5:59','6:00','6:01','6:02','6:03','6:04','6:05'],k=0;clk.textContent=times[0];
    var step=function(){k++;if(k>=times.length){mail.classList.add('arrived');return;}
      clk.textContent=times[k];clk.classList.remove('tick');void clk.offsetWidth;clk.classList.add('tick');
      setTimeout(step,k<2?420:150);};
    setTimeout(step,500);}
  if(!('IntersectionObserver' in window)){sorter.classList.add('done');document.querySelectorAll('.photo.settle').forEach(function(p){p.classList.add('seen');});return;}
  var io=new IntersectionObserver(function(es){es.forEach(function(e){
    if(!e.isIntersecting) return;
    if(e.target===sorter){setTimeout(function(){sorter.classList.add('done');},500);} else {e.target.classList.add('seen');}
    io.unobserve(e.target);
  });},{threshold:.35});
  io.observe(sorter); document.querySelectorAll('.photo.settle').forEach(function(p){io.observe(p);});
  document.getElementById('replay').addEventListener('click',function(){sorter.classList.remove('done');setTimeout(function(){sorter.classList.add('done');},700);});
  // 3D lean toward the pointer (mouse only, big screens, motion allowed)
  var deck=document.getElementById('deck');
  if(deck&&!still&&matchMedia('(hover:hover) and (pointer:fine) and (min-width:1001px)').matches){
    var hero=document.querySelector('.hero'),raf=0,px=0,py=0;
    hero.addEventListener('pointermove',function(e){var r=hero.getBoundingClientRect();px=(e.clientX-r.left)/r.width-.5;py=(e.clientY-r.top)/r.height-.5;
      if(!raf)raf=requestAnimationFrame(function(){raf=0;deck.style.setProperty('transform','rotateY('+(-8+px*10).toFixed(2)+'deg) rotateX('+(4-py*8).toFixed(2)+'deg)');});});
    hero.addEventListener('pointerleave',function(){deck.style.removeProperty('transform');});
  }
})();

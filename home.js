'use strict';
// Local demonstration controls only. No analytics or customer data collection.
const menu=document.querySelector('.nav-toggle');
const nav=document.querySelector('#navigation');
menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('is-open',open);});
nav?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{menu.setAttribute('aria-expanded','false');nav.classList.remove('is-open');}));
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu?.getAttribute('aria-expanded')==='true'){menu.setAttribute('aria-expanded','false');nav.classList.remove('is-open');menu.focus();}});
const tabs=[...document.querySelectorAll('[role="tab"]')];
function activateTab(tab,focus=false){for(const candidate of tabs){const selected=candidate===tab;candidate.setAttribute('aria-selected',String(selected));candidate.tabIndex=selected?0:-1;document.getElementById(candidate.getAttribute('aria-controls')).hidden=!selected;}if(focus)tab.focus();}
tabs.forEach((tab,index)=>{tab.addEventListener('click',()=>activateTab(tab));tab.addEventListener('keydown',event=>{let next;if(['ArrowDown','ArrowRight'].includes(event.key))next=(index+1)%tabs.length;else if(['ArrowUp','ArrowLeft'].includes(event.key))next=(index+tabs.length-1)%tabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=tabs.length-1;else return;event.preventDefault();activateTab(tabs[next],true);});});
const billing=[...document.querySelectorAll('[data-billing]')];
billing.forEach(button=>button.addEventListener('click',()=>{const yearly=button.dataset.billing==='yearly';billing.forEach(other=>other.setAttribute('aria-pressed',String(other===button)));document.getElementById('price-amount').textContent=yearly?'$390':'$39';document.getElementById('price-period').textContent=yearly?'/ year':'/ month';document.getElementById('price-detail').textContent=yearly?'US dollars. Billed yearly. Save $78 compared with 12 monthly payments.':'US dollars. Billed monthly after you choose a paid plan.';}));

// Exercises the actual loopback website. Never follows production/signup/billing destinations.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),cp=require('node:child_process');
const {chromium}=require(process.env.BIDBELL_PLAYWRIGHT_MODULE||'@playwright/test');
(async()=>{
 const output=path.resolve(process.argv[2]);fs.mkdirSync(output,{recursive:true});
 const site=path.resolve('_site');
 const walk=directory=>fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(directory,entry.name)):[path.join(directory,entry.name)]);
 const previewPages=new Set(['/','/construction-bids/','/cleaning-bids/','/start/','/subscribe/','/workspace/','/prepare/']);
 const routes=[...new Set([...previewPages,...walk(site).filter(file=>file.endsWith('.html')).map(file=>'/'+path.relative(site,file).replaceAll('\\','/').replace(/index\.html$/,''))])];
 const browser=await chromium.launch({headless:true}),results=[];
 try{
  for(const width of [375,1440]){
   const page=await browser.newPage({viewport:{width,height:1000}});
   await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
   await page.goto('http://127.0.0.1:8861/',{waitUntil:'networkidle'});
   const before=cp.execFileSync('git',['show','09408ba:index.html'],{encoding:'utf8'});
   await page.setContent(before,{waitUntil:'networkidle'});
   await page.screenshot({path:path.join(output,`homepage-before-${width}.png`),fullPage:true});
   for(const route of routes.filter(route=>!process.argv[3]||route===process.argv[3])){
    await page.goto('http://127.0.0.1:8861'+route,{waitUntil:'networkidle'});
    const data=await page.evaluate(()=>({text:document.body.innerText,width:innerWidth,scroll:document.documentElement.scrollWidth,forms:[...document.forms].map(f=>f.action),links:[...document.querySelectorAll('a[href]')].map(a=>a.href),scriptSources:[...document.scripts].map(s=>s.src)}));
    assert(data.text.includes('Staging preview'),route+' missing staging label');
    assert(data.scroll<=width+1,route+' horizontal overflow at'+width);
    assert(!data.text.includes('\uFFFD'),route+' replacement character');
    assert(!/\b([a-z]{3,})(?:\1){2,}\b/i.test(data.text),route+' joined repeated word');
    assert(!data.forms.some(url=>/docs.google.com|paddle.com/.test(url)),route+' production form');
    assert(!data.scriptSources.some(url=>/paddle.com|checkout.js/.test(url)),route+' active checkout script');
    assert(!data.links.some(url=>/^https:\/\/(?:getbidbell.com|bidbell-workspace.onrender.com)/.test(url)),route+' production action');
    if(route==='/start/')assert(data.links.some(url=>url.includes('industry=construction#register')),'construction signup is disconnected');
    if(route==='/construction-bids/')assert(data.links.some(url=>/#opportunity\/[a-f0-9]{24}$/.test(url)),'no synced opportunity deep links');
    if(route==='/'&&width===375){
     const menu=page.getByRole('button',{name:/Menu/});await menu.click();assert.equal(await menu.getAttribute('aria-expanded'),'true');
     await page.keyboard.press('Escape');assert.equal(await menu.getAttribute('aria-expanded'),'false');assert(await menu.evaluate(x=>document.activeElement===x));
     await menu.click();await page.getByRole('link',{name:'Industries',exact:true}).click();assert.equal(await menu.getAttribute('aria-expanded'),'false');
     await menu.click();await page.mouse.click(15,900);assert.equal(await menu.getAttribute('aria-expanded'),'false');
    }
    if(previewPages.has(route)){
     await page.evaluate(()=>window.scrollTo(0,0));
     const imageName=(route==='/'?'homepage-after':route.replaceAll('/','')+'-after')+`-${width}`;
     await page.screenshot({path:path.join(output,imageName+'.png'),fullPage:true});
     await page.screenshot({path:path.join(output,imageName+'-viewport.png')});
    }
    results.push({route,width,textCharacters:data.text.length,horizontalOverflow:false,productionActions:false});
   }
   await page.close();
  }
 }finally{await browser.close();}
 fs.writeFileSync(path.join(output,'website-browser-results.json'),JSON.stringify({baseline:'09408ba',site:'http://127.0.0.1:8861',screenshots:'Actual baseline and staged markup rendered in Chromium',checks:results},null,2));
 console.log(JSON.stringify({journeyPages:results.length,viewports:[375,1440],keyboardAndMobileMenu:'passed',productionActions:'blocked'}));
})().catch(error=>{console.error(error);process.exitCode=1;});

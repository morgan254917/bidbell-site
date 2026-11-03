const {chromium}=require(process.env.BIDBELL_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const base=process.env.BIDBELL_TEXT_BASE||'http://127.0.0.1:8841';
const pages=fs.readdirSync(root,{recursive:true}).filter(name=>name.endsWith('.html')&&!name.split(path.sep).some(part=>['_site','tools','.git'].includes(part)));
const patterns=[
 ['corrupted encoding',/\uFFFD|Ã[©¨¡³±¼]|â[€€™]/u],
 ['adjacent repeated words',/\b(the|your|and|please|will|for|from|into|with|are|was)\s+\1\b/i],
 ['joined repeated phrase',/\b([a-z]{4,24})\1\1\b/i],
 ['unresolved placeholder',/\{\{[^{}\n]+\}\}|\bundefined\b/i]
];
(async()=>{
 const browser=await chromium.launch();
 const problems=[];
 try{
  for(const width of [390,1280]){
   const page=await browser.newPage({viewport:{width,height:850}});
   for(const file of pages){
    const route='/'+file.replaceAll(path.sep,'/').replace(/index\.html$/,'');
    const response=await page.goto(base+route,{waitUntil:'domcontentloaded'});
    if(response.status()!==200){problems.push({width,route,status:response.status()});continue;}
    const observed=await page.locator('body').innerText();
    for(const [problem,regex] of patterns){
     const match=observed.match(regex);
     if(match)problems.push({width,route,problem,text:match[0]});
    }
   }
   await page.close();
  }
 }finally{await browser.close();}
 console.log(JSON.stringify({pages:pages.length,renderedChecks:pages.length*2,problems},null,2));
 assert.deepEqual(problems,[]);
})().catch(error=>{console.error(error);process.exitCode=1;});

/* Real rendering regression checks. Preview locally; never submits signup or payment. */
const {chromium}=require(process.env.BIDBELL_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.BIDBELL_VISUAL_BASE||'http://127.0.0.1:8832';
const output=process.env.BIDBELL_VISUAL_OUTPUT;
async function fits(page,label){
 const dimensions=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,content:document.documentElement.scrollWidth}));
 assert.ok(dimensions.content<=dimensions.viewport+1,`${label}: ${JSON.stringify(dimensions)}`);
}
(async()=>{
 const browser=await chromium.launch({headless:true});let failures=[];let checks=0;
 try{
 for(const width of [320,375,768,1280]){
 const page=await browser.newPage({viewport:{width,height:900}});
 async function check(name,fn){checks++;try{await fn()}catch(e){failures.push({width,name,error:e.message});if(output){fs.mkdirSync(output,{recursive:true});await page.screenshot({path:`${output}/failure-${width}-${name}.png`,fullPage:true})}}}
 await check('shared-navigation',async()=>{
  await page.goto(base+'/cleaning-bids/',{waitUntil:'networkidle'});const colors=await page.locator('.topbar a').evaluate(a=>({fg:getComputedStyle(a).color,bg:getComputedStyle(a.closest('.topbar')).backgroundColor}));
  const light=s=>{const v=s.match(/[\d.]+/g).slice(0,3).map(x=>{x=Number(x)/255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4});return .2126*v[0]+.7152*v[1]+.0722*v[2]};const l=[light(colors.fg),light(colors.bg)].sort((a,b)=>b-a);assert.ok((l[0]+.05)/(l[1]+.05)>=4.5,'Trial banner text must be readable on its background');await fits(page,'closed menu');
  if(width<=768){await page.locator('.menu summary').click();await fits(page,'open menu');assert.ok(await page.locator('.menu-panel a').first().isVisible());await page.keyboard.press('Escape');assert.equal(await page.locator('.menu').getAttribute('open'),null)}
 });
 await check('long-public-opportunity',async()=>{
  await page.route('**/data/service_bids.json',r=>r.fulfill({json:{updated:new Date().toISOString().slice(0,10),source:'Synthetic local layout fixture',bids:[{title:'Cleaning contract '+ 'LongReference'.repeat(60),trade:'janitorial',type:'Solicitation',agency:'Authority'+ 'LongAgency'.repeat(20),city:'Sample City',state:'TX',due:'2099-12-01',set_aside:'Eligibility'+ 'LongCriteria'.repeat(20),link:'https://sam.gov/opp/visual-fixture/view',sol:'Ref'+ 'LongReference'.repeat(12)}]}}));
  await page.goto(base+'/workspace/',{waitUntil:'networkidle'});await page.locator('#opportunities .opportunity').first().waitFor();assert.match(await page.locator('#count').innerText(),/^1 notice matches these filters\./);await fits(page,'long public card');
  await page.getByRole('button',{name:'Add to shortlist',exact:true}).click();await fits(page,'saved long public card');
  await page.locator('#query').fill('no-match-layout-fixture');assert.match(await page.locator('#opportunities').innerText(),/No notices/);await fits(page,'empty search');
 });
 await check('checklist-long-step',async()=>{
  await page.goto(base+'/prepare/',{waitUntil:'networkidle'});await page.locator('#title').fill('Synthetic visual QA');await page.locator('#new-item').fill('Reference'.repeat(55));await page.getByRole('button',{name:'Add step',exact:true}).click();await fits(page,'long checklist item');
  await page.getByRole('button',{name:'Save on this device',exact:true}).click();assert.match(await page.locator('#status').innerText(),/saved/i);await page.reload();await page.getByRole('button',{name:'Load saved checklist',exact:true}).click();assert.ok((await page.locator('#items').innerText()).includes('Reference'.repeat(55)));await fits(page,'restored checklist');
 });
 await check('signup-empty-validation',async()=>{
  await page.goto(base+'/start/',{waitUntil:'networkidle'});assert.equal(await page.locator('form').first().evaluate(f=>f.checkValidity()),false);await fits(page,'empty signup');
 });
 await page.close();
 }
 }finally{await browser.close()}
 console.log(JSON.stringify({checks,failures},null,2));if(failures.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});

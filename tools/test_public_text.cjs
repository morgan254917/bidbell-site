const {chromium}=require(process.env.BIDBELL_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch();
 try {
  const page=await browser.newPage();
  const notice={title:'Synthetic janitorial opportunity',trade:'janitorial',type:'Solicitation',agency:'Sample buyer',city:'0',state:'TX',due:'2099-12-01',set_aside:'Small business.',link:'https://sam.gov/opp/text-fixture/view',sol:'Ref'};
  await page.route('**/data/service_bids.json',r=>r.fulfill({json:{updated:new Date(Date.now()-86400000).toISOString().slice(0,10),source:'Synthetic text fixture',bids:[notice,notice]}}));
  await page.goto((process.env.BIDBELL_TEXT_BASE||'http://127.0.0.1:8841')+'/workspace/');
  await page.locator('#opportunities .opportunity').first().waitFor();
  const observed={freshness:await page.locator('#freshness').innerText(),card:await page.locator('#opportunities .opportunity').first().innerText()};
  console.log(JSON.stringify(observed));
  assert.match(observed.freshness,/1 day since the source update\./);
  assert.match(observed.freshness,/1 unsupported or duplicate record was excluded\./);
  assert.match(observed.card,/Sample buyer · TX/);
  assert.match(observed.card,/Small business\. Verify eligibility/);
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

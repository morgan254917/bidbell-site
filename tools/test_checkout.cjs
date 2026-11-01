const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../checkout.js'),'utf8');
function run(search,env='production',missing=false){
 const calls=[],error={hidden:true};
 const paddle={Environment:{set:v=>calls.push(['environment',v])},Initialize:v=>calls.push(['initialize',v]),Checkout:{open:()=>{throw new Error('Client-created checkout must not be opened');}}};
 vm.runInNewContext(source,{URLSearchParams,window:{location:{search},Paddle:missing?undefined:paddle},document:{getElementById:id=>id==='checkout-error'?error:{textContent:JSON.stringify({env,client_token:'synthetic-public-token'})}}});
 return {calls,error};
}
test('regular and old plan links do not create checkout',()=>{for(const q of ['', '?plan=yearly&c=someone','?plan=monthly'])assert.equal(run(q).calls.length,0);});
test('server transaction initializes the provider auto-open flow',()=>{const r=run('?_ptxn=txn_'+'a'.repeat(26));assert.equal(r.calls.length,1);assert.equal(r.calls[0][0],'initialize');assert.equal(r.error.hidden,true);});
test('sandbox settings remain isolated',()=>{const r=run('?_ptxn=txn_'+'b'.repeat(26),'sandbox');assert.equal(r.calls[0][0],'environment');assert.equal(r.calls[0][1],'sandbox');});
test('invalid transaction or unavailable provider fails visibly',()=>{assert.equal(run('?_ptxn=not-a-transaction').error.hidden,false);assert.equal(run('?_ptxn=txn_'+'a'.repeat(26),'production',true).error.hidden,false);});

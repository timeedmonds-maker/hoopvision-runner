import {test} from 'node:test';
import assert from 'node:assert/strict';
import {slotRequestUrl,recoverMissingWindows,recoveryAnchor} from './sdk_slot.mjs';
const job={game_id:'0022699999',program_id:'companion-0022699999-positions',start_ms:1792522800000,count:2};
const signed='https://nba-cdn.cloud.easelive.tv/a/companion-0022699999-positions/b/events/slot?token=synthetic-test-token&from=0&to=1';
test('exact authorised URL is scoped and remains in memory',()=>{
 const url=new URL(slotRequestUrl(signed,job,job.start_ms+5000));
 assert.equal(url.hostname,'nba-cdn.cloud.easelive.tv');
 assert.equal(url.searchParams.get('token'),'synthetic-test-token');
 assert.equal(url.searchParams.get('from'),String(job.start_ms+5000));
 assert.equal(url.searchParams.get('to'),String(job.start_ms+9999));
 for(const bad of [signed.replace('nba-cdn.cloud.easelive.tv','evil.example'),
  signed.replace('companion-0022699999-positions','companion-0022611111-positions'),
  signed.replace('token=synthetic-test-token','other=none'),
  'http://nba-cdn.cloud.easelive.tv/a/'+job.program_id+'/events/slot?token=test'])
  assert.throws(()=>slotRequestUrl(bad,job,job.start_ms));
 assert.throws(()=>slotRequestUrl(signed,job,job.start_ms+10000));
});
test('fallback recovers only authentic slot arrays, preserving empty observed slots',async()=>{
 const received=new Map([[job.start_ms,{from:job.start_ms,to:job.start_ms+4999,events:[]}]]);
 let attempts=0;
 const count=await recoverMissingWindows(job,received,signed,{wait:async()=>{},request:async()=>{
  attempts++;return attempts===1?{status:503,ok:false}:{status:200,ok:true,
   json:async()=>[{id:'observed-from-provider'}]};
 }});
 assert.equal(count,2);
 assert.equal(attempts,2);
 assert.deepEqual(received.get(job.start_ms).events,[]);
 assert.deepEqual(received.get(job.start_ms+5000).events,[{id:'observed-from-provider'}]);
});
test('persistent server failure leaves slot missing, never manufactures data',async()=>{
 const received=new Map();
 await assert.rejects(recoverMissingWindows({...job,count:1},received,signed,{
  wait:async()=>{},request:async()=>({status:503,ok:false})
 }),/uncovered_window/);
 assert.equal(received.size,0);
});
test('unauthorised SDK slot is rejected immediately',async()=>{
 let calls=0;
 await assert.rejects(recoverMissingWindows({...job,count:1},new Map(),signed,{
  wait:async()=>{},request:async()=>{calls++;return {status:403,ok:false};}
 }),/sdk_slot_denied/);
 assert.equal(calls,1);
});

test('post-final chunks use the same earlier observed programme anchor',()=>{
 const origin=1792522800000;
 const a={...job,start_ms:origin,part:0};
 const b={...job,start_ms:origin+7*300*5000,part:7};
 const c={...job,start_ms:origin+12*300*5000,part:12,count:120};
 const expected=origin+60*60000;
 assert.equal(recoveryAnchor(a),expected);
 assert.equal(recoveryAnchor(b),expected);
 assert.equal(recoveryAnchor(c),expected);
 assert.throws(()=>recoveryAnchor({...b,start_ms:b.start_ms+1}),/invalid_slot_anchor/);
 assert.throws(()=>recoveryAnchor({...b,part:-1}),/invalid_slot_anchor/);
});

test('bounded two-way exact-window fallback returns independently observed slots',async()=>{
 const requested=[];
 const received=new Map();
 const count=await recoverMissingWindows(job,received,signed,{
  parallel:2,wait:async()=>{},
  request:async url=>{
   const ms=Number(new URL(url).searchParams.get('from'));
   requested.push(ms);
   return {status:200,ok:true,json:async()=>[{id:'event-'+ms}]};
  }
 });
 assert.equal(count,2);
 assert.equal(received.size,2);
 assert.deepEqual(requested.sort((a,b)=>a-b),[job.start_ms,job.start_ms+5000]);
 assert.throws(()=>slotRequestUrl(signed,job,job.start_ms-5000),/invalid_slot_request/);
 await assert.rejects(recoverMissingWindows(job,new Map(),signed,{parallel:4,
  request:async()=>({status:200,ok:true,json:async()=>[]})}),/invalid_slot_parallelism/);
});

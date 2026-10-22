/** SDK-authorised, exact-window fallback. Signed session URLs live only in process memory. */
const HOST='nba-cdn.cloud.easelive.tv';
const WINDOW=5000;
const waitDefault=ms=>new Promise(resolve=>setTimeout(resolve,ms));

/** A known in-game slot used only to obtain the SDK-issued signed session URL. */
export function recoveryAnchor(job){
 if(!Number.isSafeInteger(job?.start_ms)||job.start_ms%WINDOW!==0||
    !Number.isSafeInteger(job?.part)||job.part<0||job.part>50)
  throw Error('invalid_slot_anchor');
 const origin=job.start_ms-job.part*300*WINDOW;
 const anchor=origin+60*60000;
 if(!Number.isSafeInteger(anchor)||anchor%WINDOW!==0)throw Error('invalid_slot_anchor');
 return anchor;
}

export function slotRequestUrl(observed,job,ms){
 if(typeof observed!=='string'||!observed)throw Error('sdk_session_url_missing');
 if(!Number.isSafeInteger(ms)||ms%WINDOW!==0||!Number.isSafeInteger(job?.start_ms)
  ||!Number.isSafeInteger(job?.count)||ms<job.start_ms
  ||ms>=job.start_ms+job.count*WINDOW)throw Error('invalid_slot_request');
 let u;
 try{u=new URL(observed);}catch{throw Error('sdk_session_url_invalid');}
 if(u.protocol!=='https:'||u.hostname!==HOST||u.port||u.username||u.password
  ||!u.pathname.includes('/'+job.program_id+'/')
  ||!u.pathname.endsWith('/events/slot')||!u.searchParams.get('token'))
  throw Error('sdk_session_url_invalid');
 u.searchParams.set('from',String(ms));
 u.searchParams.set('to',String(ms+WINDOW-1));
 return u.toString();
}

/** Never substitute an empty window on HTTP/network failure. Every slot must be observed. */
/** Bounded parallel slot recovery: only SDK-issued session URLs, exact 5s requests.
 *  Limit in-flight requests to four per game checkpoint to avoid hammering the feed.
 *  Every missing slot remains a hard error; never generate synthetic empty rows.
 */
export async function recoverMissingWindows(job,received,observedUrl,
 {request=fetch,wait=waitDefault}={}){
 const windows=Array.from({length:job.count},(_,i)=>job.start_ms+i*WINDOW);
 const missing=windows.filter(ms=>!received.has(ms));
 const statuses={};
 let networkErrors=0,invalidBodies=0,cursor=0,denied=false;
 const worker=async()=>{
  while(!denied){
   const i=cursor++;
   if(i>=missing.length)return;
   const ms=missing[i],url=slotRequestUrl(observedUrl,job,ms);
   for(let attempt=0;attempt<4&&!received.has(ms);attempt++){
    let response;
    try{
     response=await request(url,{signal:AbortSignal.timeout(16000),headers:{
      Accept:'application/json',Referer:'https://www.nba.com/',
      'User-Agent':'Mozilla/5.0 (compatible; licensed Game Pulse SDK collector)'}});
    }catch{networkErrors++;}
    if(response){
     const status=Number.isInteger(response.status)?response.status:0;
     const bucket=status===200?'200':String(status);
     statuses[bucket]=(statuses[bucket]||0)+1;
     if(status===401||status===403){denied=true;break;}
     if(response.ok){
      try{
       const events=await response.json();
       if(Array.isArray(events))received.set(ms,{from:ms,to:ms+WINDOW-1,events});
       else invalidBodies++;
      }catch{invalidBodies++;}
     }
    }
    if(!received.has(ms)&&attempt<3&&!denied)await wait((attempt+1)*1000);
   }
  }
 };
 await Promise.allSettled(Array.from({length:Math.min(4,missing.length)},()=>worker()));
 const remaining=windows.filter(ms=>!received.has(ms)).length;
 if(remaining||denied){
  // No signed URLs, bodies, tokens, exact request times or player records in logs.
  console.log('SDK_SLOT_COVERAGE_DIAGNOSTIC',JSON.stringify({
   game_id:job.game_id,part:job.part,expected:windows.length,
   accepted:windows.length-remaining,remaining,
   http_status_counts:statuses,network_errors:networkErrors,invalid_bodies:invalidBodies}));
 }
 if(denied)throw Error('sdk_slot_denied');
 if(remaining)throw Error('uncovered_window');
 return windows.length;
}

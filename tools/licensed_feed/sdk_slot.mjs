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
export async function recoverMissingWindows(job,received,observedUrl,
 {request=fetch,wait=waitDefault}={}){
 const windows=Array.from({length:job.count},(_,i)=>job.start_ms+i*WINDOW);
 for(const ms of windows){
  if(received.has(ms))continue;
  const url=slotRequestUrl(observedUrl,job,ms);
  for(let attempt=0;attempt<4&&!received.has(ms);attempt++){
   let response;
   try{
    response=await request(url,{signal:AbortSignal.timeout(16000),headers:{
     Accept:'application/json',Referer:'https://www.nba.com/',
     'User-Agent':'Mozilla/5.0 (compatible; licensed Game Pulse SDK collector)'}});
   }catch{}
   if(response){
    if([401,403,404].includes(response.status))throw Error('sdk_slot_denied');
    if(response.ok){
     try{
      const events=await response.json();
      if(Array.isArray(events))received.set(ms,{from:ms,to:ms+WINDOW-1,events});
     }catch{}
    }
   }
   if(!received.has(ms)&&attempt<3)await wait((attempt+1)*1000);
  }
 }
 if(windows.some(ms=>!received.has(ms)))throw Error('uncovered_window');
 return windows.length;
}

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,copyFileSync,mkdirSync,rmSync,readFileSync} from 'node:fs';
import {join,basename} from 'node:path';
import {tmpdir} from 'node:os';
import {pilotJob,PRIVATE_REPO,privateTag,assertScopedContext,verifyAndStore} from './github_private_release.mjs';

const fixture=()=>{
 const dir=mkdtempSync(join(tmpdir(),'fake-github-private-'));
 const job=pilotJob();
 writeFileSync(join(dir,'checkpoint.tar.gz'),Buffer.from('synthetic-test-archive-not-NBA'));
 writeFileSync(join(dir,'manifest.json'),JSON.stringify({
   schema:'nba-gamepulse-sdk-chunk.v1',game_id:job.game_id,
   part:job.part,start_ms:job.start_ms,successful_windows:300,
   unique_keyframes:20,frames_with_players:15,frames_with_ball:12})+'\n');
 return {dir,job};
};
function fakeGithub(remote,record,corrupt=false){
 let exists=false;
 const assets=new Map();
 return args=>{
   record.push([...args]);
   const normalized=args.join(' ');
   if(args.includes('--repo')&&args[args.indexOf('--repo')+1]!==PRIVATE_REPO)
     throw Error('private_destination_violation');
   if(args[0]!=='release')throw Error('unexpected_action');
   if(args[1]==='view')return exists?{
     ok:true,stdout:JSON.stringify({assets:[...assets.keys()].map(name=>({name}))})
   }:{ok:false,stdout:''};
   if(args[1]==='create'){exists=true;return {ok:true,stdout:''};}
   if(args[1]==='upload'){
     assert.equal(exists,true);
     const local=args[3];
     const name=basename(local);
     copyFileSync(local,join(remote,name));
     assets.set(name,true);
     return {ok:true,stdout:''};
   }
   if(args[1]==='download'){
     const name=args[args.indexOf('--pattern')+1];
     const dest=args[args.indexOf('--dir')+1];
     mkdirSync(dest,{recursive:true});
     const bytes=readFileSync(join(remote,name));
     writeFileSync(join(dest,name),corrupt?Buffer.concat([bytes,Buffer.from('tampered')]):bytes);
     return {ok:true,stdout:''};
   }
   throw Error('unexpected_gh_action');
 };
}
test('fails closed outside main manual approval and missing secret',()=>{
 const env={GITHUB_REPOSITORY:'timeedmonds-maker/hoopvision-runner',
   GITHUB_REF:'refs/heads/main',GITHUB_EVENT_NAME:'workflow_dispatch',GH_TOKEN:'x'.repeat(35)};
 assert.doesNotThrow(()=>assertScopedContext(env));
 for(const bad of [
   {...env,GITHUB_EVENT_NAME:'pull_request'},
   {...env,GITHUB_REF:'refs/heads/malicious'},
   {...env,GITHUB_REPOSITORY:'other/repo'},
   {...env,GH_TOKEN:''}
 ])assert.throws(()=>assertScopedContext(bad));
});
test('acceptance tag exclusively targets verified test game',()=>{
 const j=pilotJob();
 assert.equal(privateTag(j),'gamepulse-sdk-github-acceptance-'+j.game_id);
 assert.throws(()=>privateTag({...j,part:1}));
 assert.throws(()=>privateTag({...j,count:299}));
});
test('public workflow fake-gh writes only to private release and verifies downloaded bytes',()=>{
 const {dir,job}=fixture(), remote=mkdtempSync(join(tmpdir(),'fake-private-release-'));
 const calls=[];
 try{
  assert.equal(verifyAndStore(job,dir,fakeGithub(remote,calls)),
   'PRIVATE_GITHUB_SHA_READBACK_CERTIFIED');
  assert.equal(calls.filter(c=>c[1]==='create').length,1);
  assert.equal(calls.filter(c=>c[1]==='upload').length,2);
  assert.equal(calls.filter(c=>c[1]==='download').length,2);
  assert(calls.every(c=>c.includes('--repo')&&c.includes(PRIVATE_REPO)));
  assert(calls.every(c=>!c.includes('--clobber')));
 }finally{rmSync(dir,{force:true,recursive:true});rmSync(remote,{force:true,recursive:true});}
});
test('private archive corruption blocks success',()=>{
 const {dir,job}=fixture(),remote=mkdtempSync(join(tmpdir(),'fake-private-release-'));
 try{
   assert.throws(()=>verifyAndStore(job,dir,fakeGithub(remote,[],true)),/private_sha_mismatch/);
 }finally{rmSync(dir,{force:true,recursive:true});rmSync(remote,{force:true,recursive:true});}
});
test('missing player evidence fails before network access',()=>{
 const {dir,job}=fixture();
 try{
  const p=join(dir,'manifest.json');
  const info=JSON.parse(readFileSync(p));
  info.frames_with_players=0;
  writeFileSync(p,JSON.stringify(info));
  assert.throws(()=>verifyAndStore(job,dir,()=>{throw Error('should never call network')}),/capture_qa_failed/);
 }finally{rmSync(dir,{force:true,recursive:true});}
});

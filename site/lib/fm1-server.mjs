import { ID, PublicError, PROFILES, RESOURCE_URI, TOOLS, sanitize, validate } from './fm1-contract.mjs';
import { UI_HTML } from './fm1-ui.mjs';
import { ICONS } from './fm1-icon.mjs';

const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const ident=()=>crypto.randomUUID().replaceAll('-','');
const now=()=>Math.floor(Date.now()/1000);
const result=(data)=>({content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data});
async function body(request) {
  if(Number(request.headers.get('content-length')||0)>65536)throw new PublicError('Request too large.',413);
  const raw=await request.text();
  if(raw.length>65536)throw new PublicError('Request too large.',413);
  try{return JSON.parse(raw);}catch{throw new PublicError('Invalid JSON.');}
}
const parse=(row)=>row?{id:row.id,operation:row.operation,state:row.state,created:row.created,...(row.result?JSON.parse(row.result):{})}:null;
function db(env){if(!env.DB)throw new PublicError('Saved requests are unavailable.',503);return env.DB;}
function user(request){const value=request.headers.get('oai-authenticated-user-id');if(!value)throw new PublicError('Sign in to use your FM1 library.',401);return value;}
function safeOrigin(request,env){const origin=request.headers.get('origin');if(origin&&origin!==(env.SITE_ORIGIN||new URL(request.url).origin))throw new PublicError('Origin is not permitted.',403);}
async function relayState(env) {
  const row=await db(env).prepare("SELECT last_seen,allow_switch FROM relay_state WHERE id='bench'").first();
  return {connected:!!row&&now()-row.last_seen<30,last_seen:row?.last_seen??null,allow_switch:!!row?.allow_switch};
}
async function latest(env,owner,operation){const row=await db(env).prepare("SELECT result FROM relay_tasks WHERE user_id=? AND operation=? AND state='succeeded' ORDER BY created DESC,rowid DESC LIMIT 1").bind(owner,operation).first();return row?.result?JSON.parse(row.result).data:null;}
async function library(env,owner){
  return {profiles:PROFILES,relay:await relayState(env),catalog:await latest(env,owner,'catalog'),inventory:await latest(env,owner,'status'),
    recent_requests:(await db(env).prepare('SELECT * FROM relay_tasks WHERE user_id=? ORDER BY created DESC,rowid DESC LIMIT 12').bind(owner).all()).results.map(parse)};
}
async function enqueue(env,owner,operation,args,taskId=ident()){
  const connection=await relayState(env);
  if(!connection.connected)throw new PublicError('Bench connection is offline. Reconnect the relay before requesting fresh data.',503);
  if(operation==='switch_app'&&!connection.allow_switch)throw new PublicError('App switching is disabled at the bench.',403);
  const existing=await db(env).prepare('SELECT * FROM relay_tasks WHERE id=? AND user_id=?').bind(taskId,owner).first();
  if(existing)return {request_id:existing.id,delivery:existing.state};
  await db(env).prepare('INSERT INTO relay_tasks(id,user_id,operation,arguments,state,created) VALUES(?,?,?,?,?,?)').bind(taskId,owner,operation,JSON.stringify(args),'pending',now()).run();
  return {request_id:taskId,delivery:'pending',...(operation==='plan_app'||operation==='switch_app'?{job_id:taskId}:{}),message:'Saved request. Inspect this ID; do not submit another request after a timeout.'};
}
async function stagedSwitch(env,owner,args){
  const connection=await relayState(env);
  if(!connection.connected||!connection.allow_switch)throw new PublicError('App switching is disabled or the bench is disconnected.',403);
  const catalog=await latest(env,owner,'catalog');
  const variant=catalog?.apps?.flatMap(app=>app.variants||[]).find(item=>item.id===args.catalog_id);
  if(!variant||!variant.ready||!/^[a-f0-9]{64}$/.test(variant.sha256))throw new PublicError('Refresh packages and choose a validated, ready variant.',409);
  const approval=ident();
  await db(env).prepare('INSERT INTO switch_approvals(id,user_id,catalog_id,digest,entry_method,expires,used) VALUES(?,?,?,?,?,?,0)').bind(approval,owner,args.catalog_id,variant.sha256,args.entry_method,now()+180).run();
  return {review:{title:variant.title,variant:variant.variant,sha256:variant.sha256,catalog_id:variant.id,entry_method:args.entry_method,expires:now()+180},_approval:approval,message:'Review the variant in the library and click Confirm app switch. No device write has been submitted.'};
}
async function commitSwitch(env,owner,args){
  const approval=await db(env).prepare('SELECT * FROM switch_approvals WHERE id=? AND user_id=?').bind(args.approval_id,owner).first();
  if(!approval)throw new PublicError('This approval was not found. Review the app again.',409);
  if(approval.used){const previous=await db(env).prepare('SELECT id,state FROM relay_tasks WHERE id=? AND user_id=?').bind(approval.id,owner).first();if(previous)return {request_id:previous.id,job_id:previous.id,delivery:previous.state};throw new PublicError('Approval was already consumed; inspect the saved request.',409);}
  if(approval.expires<now())throw new PublicError('This approval has expired. Review the app again.',409);
  const connection=await relayState(env);
  if(!connection.connected||!connection.allow_switch)throw new PublicError('App switching is disabled or the bench is disconnected.',403);
  const catalog=await latest(env,owner,'catalog');
  const variant=catalog?.apps?.flatMap(app=>app.variants||[]).find(item=>item.id===approval.catalog_id);
  if(!variant?.ready||variant.sha256!==approval.digest)throw new PublicError('Package readiness changed. Refresh and review again.',409);
  // Approval consumption and queue insertion are one D1 transaction. The same
  // approval ID is also the durable bridge job ID; retries can only inspect it.
  const committedAt=now();
  await db(env).batch([
    db(env).prepare('INSERT INTO relay_tasks(id,user_id,operation,arguments,state,created) SELECT id,user_id,?,?,?,? FROM switch_approvals WHERE id=? AND user_id=? AND used=0 AND expires>=?').bind('switch_app',JSON.stringify({catalog_id:approval.catalog_id,entry_method:approval.entry_method,expected_sha256:approval.digest,approval_expires:approval.expires}),'pending',committedAt,approval.id,owner,committedAt),
    db(env).prepare('UPDATE switch_approvals SET used=1 WHERE id=? AND user_id=? AND used=0 AND expires>=?').bind(approval.id,owner,committedAt),
  ]);
  const saved=await db(env).prepare('SELECT id,state FROM relay_tasks WHERE id=? AND user_id=?').bind(approval.id,owner).first();
  if(!saved)throw new PublicError('This approval has expired. Review the app again.',409);
  return {request_id:saved.id,job_id:saved.id,delivery:saved.state,message:'Confirmed request saved. Follow this job ID; do not resubmit after a disconnect.'};
}
export async function callTool(env,owner,name,input){
  const args=validate(name,input);
  if(name==='open_fm1_library')return library(env,owner);
  if(name==='get_fm1_request'){
    const row=await db(env).prepare('SELECT * FROM relay_tasks WHERE id=? AND user_id=?').bind(args.request_id,owner).first();
    if(!row)throw new PublicError('Saved request was not found.',404);
    return parse(row);
  }
  if(name==='prepare_fm1_switch')return stagedSwitch(env,owner,args);
  if(name==='confirm_fm1_switch')return commitSwitch(env,owner,args);
  return enqueue(env,owner,{get_fm1_status:'status',list_fm1_apps:'catalog',plan_fm1_app:'plan_app',get_fm1_job:'job'}[name],args);
}
async function relayRequest(request,env,path){
  if(request.method!=='POST')return json({error:'POST required.'},405);
  const configured=env.FM1_RELAY_TOKEN;
  if(!configured||configured.length<32||request.headers.get('authorization')!=='Bearer '+configured)throw new PublicError('Relay authentication required.',401);
  const value=await body(request);
  if(path==='/relay/heartbeat'){
    if(!value||Object.keys(value).some(key=>key!=='allow_switch')||typeof value.allow_switch!=='boolean')throw new PublicError('Invalid heartbeat.');
    await db(env).prepare("INSERT INTO relay_state(id,last_seen,allow_switch) VALUES('bench',?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,allow_switch=excluded.allow_switch").bind(now(),Number(value.allow_switch)).run();
    return json({connected:true});
  }
  if(path==='/relay/poll'){
    if(!value||Object.keys(value).length)throw new PublicError('Poll takes no arguments.');
    const state=await relayState(env);
    if(!state.connected)return json({tasks:[],connected:false});
    await db(env).prepare("UPDATE relay_tasks SET state='failed',result=? WHERE state='pending' AND created<?").bind(JSON.stringify({status:'failed',error:'Request expired before bench delivery. Review and submit a fresh request deliberately.'}),now()-180).run();
    // Claimed requests may be delivered again after a disconnect, always with
    // the same ID. The agent's durable journal prevents another bridge POST.
    const task=await db(env).prepare("SELECT * FROM relay_tasks WHERE state='pending' OR (state='dispatched' AND dispatched<?) ORDER BY created,rowid LIMIT 1").bind(now()-15).first();
    if(!task)return json({tasks:[],connected:true});
    const claim=await db(env).prepare("UPDATE relay_tasks SET state='dispatched',dispatched=? WHERE id=? AND (state='pending' OR (state='dispatched' AND dispatched<?))").bind(now(),task.id,now()-15).run();
    if(!claim.meta?.changes)return json({tasks:[],connected:true});
    return json({connected:true,tasks:[{id:task.id,operation:task.operation,arguments:JSON.parse(task.arguments)}]});
  }
  if(path==='/relay/result'){
    if(!value||!ID.test(value.id||'')||!['succeeded','failed','unknown'].includes(value.status)||Object.keys(value).some(key=>!['id','status','data','error'].includes(key)))throw new PublicError('Invalid relay result.');
    const task=await db(env).prepare('SELECT * FROM relay_tasks WHERE id=?').bind(value.id).first();
    if(!task||task.state==='pending')throw new PublicError('Request was not dispatched.',409);
    const clean={status:value.status,...(value.data!==undefined?{data:sanitize(value.data)}:{}),...(value.error?{error:sanitize(String(value.error))}:{})};
    const encoded=JSON.stringify(clean);
    if(encoded.length>60000)throw new PublicError('Result is too large.',413);
    if(task.result){if(task.result!==encoded)throw new PublicError('A different result is already saved.',409);return json({saved:true});}
    const saved=await db(env).prepare('UPDATE relay_tasks SET state=?,result=? WHERE id=? AND result IS NULL').bind(value.status,encoded,value.id).run();
    if(!saved.meta?.changes){const current=await db(env).prepare('SELECT result FROM relay_tasks WHERE id=?').bind(value.id).first();if(current?.result!==encoded)throw new PublicError('A different result is already saved.',409);}
    return json({saved:true});
  }
  throw new PublicError('Unknown relay route.',404);
}
async function mcp(request,env){
  if(request.method!=='POST')return json({error:'Use stateless POST /mcp.'},405);
  safeOrigin(request,env);
  const rpc=await body(request);
  if(!rpc||rpc.jsonrpc!=='2.0'||typeof rpc.method!=='string'||Array.isArray(rpc))return json({jsonrpc:'2.0',id:null,error:{code:-32600,message:'Invalid request.'}},400);
  if(rpc.id===undefined){if(rpc.method.startsWith('notifications/'))return new Response(null,{status:202});return json({error:'Request ID required.'},400);}
  try{
    let value;
    if(rpc.method==='initialize')value={protocolVersion:'2025-11-25',capabilities:{tools:{},resources:{}},serverInfo:{name:'FM1 App Library',version:'1.0.0',icons:ICONS},instructions:'Inspect saved request IDs after a disconnect. Offline planning does not authorize app switching. Actual switching requires explicit human confirmation and enabled bench capability.'};
    else if(rpc.method==='ping')value={};
    else if(rpc.method==='tools/list')value={tools:TOOLS};
    else if(rpc.method==='resources/list')value={resources:[{uri:RESOURCE_URI,name:'FM1 App Library',mimeType:'text/html;profile=mcp-app'}]};
    else if(rpc.method==='resources/read'){
      if(rpc.params?.uri!==RESOURCE_URI)throw new PublicError('Unknown UI resource.',404);
      value={contents:[{uri:RESOURCE_URI,mimeType:'text/html;profile=mcp-app',text:UI_HTML,_meta:{ui:{prefersBorder:true,csp:{connectDomains:[],resourceDomains:[]}},'openai/ui':{availableDisplayModes:['inline','fullscreen'],preferredDisplayMode:'fullscreen'}}}]};
    }else if(rpc.method==='tools/call'){
      const owner=user(request);
      try{
        const data=await callTool(env,owner,rpc.params?.name,rpc.params?.arguments||{});
        if(data._approval){const {_approval,...publicData}=data;value={...result(publicData),_meta:{approval_id:_approval}};}else value=result(data);
      }catch(error){if(error instanceof PublicError)value={isError:true,content:[{type:'text',text:error.message}],structuredContent:{error:error.message}};else throw error;}
    }else return json({jsonrpc:'2.0',id:rpc.id,error:{code:-32601,message:'Method not found.'}});
    return json({jsonrpc:'2.0',id:rpc.id,result:value});
  }catch(error){return json({jsonrpc:'2.0',id:rpc.id,error:{code:error instanceof PublicError?-32602:-32603,message:error instanceof PublicError?error.message:'Request unavailable.'}});}
}
export async function handleFm1Request(request,env){
  const path=new URL(request.url).pathname;
  try{
    if(path==='/mcp')return await mcp(request,env);
    if(path.startsWith('/relay/'))return await relayRequest(request,env,path);
    if(path==='/api/fm1'){
      if(request.method!=='POST')return json({error:'POST required.'},405);
      safeOrigin(request,env);const owner=user(request);const input=await body(request);
      if(!input||Object.keys(input).some(key=>!['name','arguments'].includes(key)))throw new PublicError('Invalid tool request.');
      const data=await callTool(env,owner,input.name,input.arguments||{});
      return json(result(data));
    }
    if(path==='/'&&request.method==='GET')return new Response(UI_HTML,{headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}});
    return null;
  }catch(error){if(!(error instanceof PublicError))console.error('FM1 storage/request failure:',error instanceof Error?error.message:'Unknown error');return json({error:error instanceof PublicError?error.message:'The library is temporarily unavailable.'},error instanceof PublicError?error.status:503);}
}

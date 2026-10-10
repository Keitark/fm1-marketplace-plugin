import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { UI_HTML } from '../lib/fm1-ui.mjs';
import { callTool } from '../lib/fm1-server.mjs';
import { database, connect, cacheCatalog, cacheInventory, digest } from './d1.mjs';

const tick=()=>new Promise(resolve=>setTimeout(resolve,15));
async function panel({embedded=false,initial=true,serverTools=true,inventory=null,official=false,loseConfirmationReply=false}={}){
  const env=database();connect(env,true,official);cacheCatalog(env);if(inventory)cacheInventory(env,'alice',inventory);
  const nodes=new Map(),registered=new Map(),requests=[],requestArgs=[],events=new Map(),notifications=[];
  function node(id){if(!nodes.has(id))nodes.set(id,{textContent:'',innerHTML:'',value:'',hidden:true,open:false,style:{},querySelectorAll:()=>[],querySelector:()=>null,removeAttribute(){},showModal(){this.open=true;},close(){this.open=false;},addEventListener(name,fn){this[name]=fn;}});return nodes.get(id);}
  const initialData=await callTool(env,'alice','open_fm1_library',{});
  if(inventory)initialData.inventory=inventory;
  const window={addEventListener(name,fn,options){events.set(name,fn);options?.signal?.addEventListener('abort',()=>events.delete(name));},removeEventListener(name){events.delete(name);}};
  const parent=embedded?{postMessage(message){notifications.push(message);if(message.id===undefined||!message.method)return;queueMicrotask(async()=>{
    let response;
    try{
      const result=message.method==='ui/initialize'?{protocolVersion:'2026-01-26',hostInfo:{name:'FM1 fixture host',version:'1'},hostCapabilities:serverTools?{serverTools:{}}:{},hostContext:{theme:'dark',displayMode:'fullscreen'}}:toolResult(await backend(message.params.name,message.params.arguments));
      if(loseConfirmationReply&&message.params?.name?.startsWith('confirm_'))throw new Error('Confirmation reply lost.');
      response={result};
    }catch(error){response={error:{code:-32000,message:error.message}};}
    events.get('message')?.({source:parent,data:{jsonrpc:'2.0',id:message.id,...response}});
    if(message.method==='ui/initialize'&&initial)events.get('message')?.({source:parent,data:{jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{content:[],structuredContent:initialData}}});
  });}}:window;
  window.parent=parent;
  function toolResult(answer){const {_approval,...data}=answer;return {content:[],structuredContent:data,...(_approval?{_meta:{approval_id:_approval}}:{})};}
  async function backend(name,args){requests.push(name);requestArgs.push({name,args});const answer=await callTool(env,'alice',name,args);if(answer.request_id){env.DB.sqlite.prepare('UPDATE relay_tasks SET state=?,result=? WHERE id=?').run('succeeded',JSON.stringify({status:'succeeded',data:{id:args.job_id||answer.job_id||answer.request_id,status:'succeeded',simulation:true}}),answer.request_id);}return answer;}
  const document={body:{classList:{add(){}},dataset:{}},getElementById:node,modelContext:{async registerTool(tool,{signal}){registered.set(tool.name,tool);signal.addEventListener('abort',()=>registered.delete(tool.name));}}};
  const context=vm.createContext({document,window,AbortController,Map,Object,Number,JSON,RegExp,String,Error,URL,TextEncoder,TextDecoder,crypto,queueMicrotask,setTimeout:(fn,ms)=>setTimeout(fn,ms>=10000?500:1),clearTimeout,fetch:async(_url,options)=>{const input=JSON.parse(options.body);try{const answer=await backend(input.name,input.arguments);if(loseConfirmationReply&&input.name.startsWith('confirm_'))throw new Error('Confirmation reply lost.');return {ok:true,json:async()=>({structuredContent:answer})};}catch(error){return {ok:false,json:async()=>({error:error.message})};}}});
  for(const script of UI_HTML.matchAll(/<script>([\s\S]*?)<\/script>/g))vm.runInContext(script[1],context);
  await tick();
  return {env,nodes,registered,requests,requestArgs,events,notifications,parent,window,node,async invoke(name,args){return registered.get(name).execute(args);},dispose(){events.get('pagehide')?.();}};
}
test('host initial tool result renders without a duplicate library request',async()=>{const p=await panel({embedded:true});assert.equal(p.node('relay-state').textContent,'Connected');assert.equal(p.requests.length,0);assert.equal(p.registered.size,0);p.dispose();});
test('initial host result renders even without serverTools capability',async()=>{const p=await panel({embedded:true,serverTools:false});assert.equal(p.node('relay-state').textContent,'Connected');assert.equal(p.requests.length,0);p.dispose();});
test('native plugin opens on device controls with detected port and no duplicate refresh',async()=>{const p=await panel({embedded:true,inventory:{device:{serial_ports:[{port:'COM7'}],session_configured:false},engine:{active:null,blocked_unknown:false}}});assert.equal(p.node('surface-label').textContent,'FM1 plugin');assert.equal(p.node('device-heading').textContent,'FM1 on COM7');assert.equal(p.node('physical-device').textContent,'FM1 on COM7');assert.equal(p.requests.length,0);p.dispose();});
test('host with serverTools falls back once if initial result absent',async()=>{const p=await panel({embedded:true,initial:false});assert.deepEqual(p.requests,['open_fm1_library']);p.dispose();});
test('resource teardown is acknowledged and aborts the panel lifecycle',async()=>{const p=await panel({embedded:true});p.events.get('message')({source:p.parent,data:{jsonrpc:'2.0',id:91,method:'ui/resource-teardown',params:{}}});await tick();const ack=p.notifications.find(m=>m.id===91);assert.deepEqual(JSON.parse(JSON.stringify(ack)),{jsonrpc:'2.0',id:91,result:{}});const n=p.requests.length;p.node('refresh').onclick();await tick();assert.equal(p.requests.length,n);p.dispose();});
test('top-level document registers seven stage-only tools and abort removes them',async()=>{const p=await panel();assert.equal(p.registered.size,7);for(const name of ['confirm_fm1_switch','confirm_fm1_official_update'])assert.ok(!p.registered.has(name));p.dispose();assert.equal(p.registered.size,0);});
test('WebMCP review opens a dialog without exposing approval or submitting write',async()=>{const p=await panel();const reviewed=await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});assert.equal(p.node('approval').open,true);assert.ok(!('_approval' in reviewed));const nonce=p.env.DB.sqlite.prepare('SELECT id FROM switch_approvals').get().id;assert.ok(!JSON.stringify(reviewed).includes(nonce));assert.ok(!p.requests.includes('confirm_fm1_switch'));p.dispose();});
test('programmatic confirmation cannot consume the approval',async()=>{const p=await panel();await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});p.node('confirm').onclick({isTrusted:false});await tick();assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM switch_approvals').get().used,0);assert.equal(p.node('approval').open,true);p.dispose();});
test('cancel and Escape clear approval before any later click',async()=>{for(const mode of ['cancel','escape']){const p=await panel();await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});if(mode==='cancel')p.node('cancel').onclick();else p.node('approval').cancel();p.node('confirm').onclick({isTrusted:true});await tick();assert.ok(!p.requests.includes('confirm_fm1_switch'));p.dispose();}});
test('trusted confirmation uses the displayed approval once',async()=>{const p=await panel();await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});p.node('confirm').onclick({isTrusted:true});p.node('confirm').onclick({isTrusted:true});await tick();assert.equal(p.requests.filter(name=>name==='confirm_fm1_switch').length,1);assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM switch_approvals').get().used,1);p.dispose();});
test('Inspect job awaits authoritative result and preserves the original job ID',async()=>{const p=await panel();const id='e'.repeat(32);p.node('job-id').value=id;p.node('inspect').onclick();await tick();assert.ok(p.requests.includes('get_fm1_request'));assert.match(p.node('detail').textContent,/succeeded/);assert.match(p.node('detail').textContent,new RegExp(id));assert.equal(p.node('job-id').value,id);p.dispose();});
test('refreshing metadata preserves a saved job for later inspection',async()=>{const p=await panel();const id='e'.repeat(32);p.node('job-id').value=id;await p.invoke('refresh_fm1_library',{});assert.equal(p.node('job-id').value,id);p.node('inspect').onclick();await tick();assert.equal(p.requestArgs.find(r=>r.name==='get_fm1_job').args.job_id,id);p.dispose();});
test('lost confirmation reply retains the committed job ID and inspection does not resubmit',async()=>{const p=await panel({loseConfirmationReply:true});await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});const id=p.env.DB.sqlite.prepare('SELECT id FROM switch_approvals').get().id;p.node('confirm').onclick({isTrusted:true});await tick();assert.equal(p.node('job-id').value,id);assert.match(p.node('message').textContent,/Inspect job/);assert.match(p.node('message').textContent,new RegExp(id));assert.equal(p.env.DB.sqlite.prepare("SELECT COUNT(*) AS n FROM relay_tasks WHERE operation='switch_app'").get().n,1);p.node('inspect').onclick();await tick();assert.equal(p.requestArgs.find(r=>r.name==='get_fm1_job').args.job_id,id);assert.equal(p.requests.filter(name=>name==='confirm_fm1_switch').length,1);assert.equal(p.env.DB.sqlite.prepare("SELECT COUNT(*) AS n FROM relay_tasks WHERE operation='switch_app'").get().n,1);assert.match(p.node('detail').textContent,new RegExp(id));p.dispose();});
test('WebMCP inspection selects the exact job ID in the recovery field',async()=>{const p=await panel();const id='e'.repeat(32);await p.invoke('inspect_fm1_job',{job_id:id});assert.equal(p.node('job-id').value,id);assert.match(p.node('detail').textContent,new RegExp(id));p.dispose();});
test('every browser tool rejects malformed arguments without backend call',async()=>{const p=await panel();const n=p.requests.length;for(const tool of p.registered.values())await assert.rejects(tool.execute({unexpected:'x'}),/arguments/);await assert.rejects(p.invoke('plan_fm1_app',{catalog_id:'Bad-ID'}),/Invalid/);assert.equal(p.requests.length,n);p.dispose();});

function detectedInventory(mode='sysex'){
  const official=['sysex','ota_sysex'].includes(mode);
  return {device:{update_mode:{mode,app_entry_method:mode==='serial'?'serial':mode==='uboot'?'already_uboot':null,official_available:official},
    official_update:{configured:true,available:official,sha256:digest,package_format:'.fwsc',handoff:true}},
    engine:{active:null,blocked_unknown:false,updater_handoff:false,storage_fault:false}};
}

test('official WebMCP review is stage-only and keeps nonce out of returned review and dialog',async()=>{
  const p=await panel({official:true,inventory:detectedInventory()});
  const review=await p.invoke('start_fm1_official_update_review',{});
  const approval=p.env.DB.sqlite.prepare('SELECT id,used FROM official_update_approvals').get();
  assert.equal(p.node('approval').open,true);assert.equal(p.node('approval-title').textContent,'Open official updater');
  assert.equal(review.review.sha256,digest);assert.equal(review.review.package_format,'.fwsc');
  assert.ok(!JSON.stringify(review).includes(approval.id));assert.ok(!p.node('review').innerHTML.includes(approval.id));
  assert.match(p.node('review').innerHTML,/\.fwsc/);assert.match(p.node('review').innerHTML,new RegExp(digest));
  assert.equal(approval.used,0);assert.ok(!p.requests.includes('confirm_fm1_official_update'));
  assert.equal(p.env.DB.sqlite.prepare("SELECT count(*) AS n FROM relay_tasks WHERE operation='official_updater'").get().n,0);
  p.dispose();
});

test('official synthetic confirmation leaves review open and trusted click consumes displayed approval once',async()=>{
  const p=await panel({official:true,inventory:detectedInventory()});
  await p.invoke('start_fm1_official_update_review',{});
  const id=p.env.DB.sqlite.prepare('SELECT id FROM official_update_approvals').get().id;
  p.node('confirm').onclick({isTrusted:false});await tick();
  assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM official_update_approvals').get().used,0);
  assert.equal(p.node('approval').open,true);assert.ok(!p.requests.includes('confirm_fm1_official_update'));
  p.node('confirm').onclick({isTrusted:true});p.node('confirm').onclick({isTrusted:true});await tick();
  assert.equal(p.requests.filter(name=>name==='confirm_fm1_official_update').length,1);
  assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM official_update_approvals').get().used,1);
  assert.equal(p.node('job-id').value,id);
  assert.equal(p.requestArgs.find(item=>item.name==='confirm_fm1_official_update').args.approval_id,id);
  assert.equal(p.env.DB.sqlite.prepare("SELECT count(*) AS n FROM relay_tasks WHERE operation='official_updater'").get().n,1);
  p.dispose();
});

test('official Cancel and Escape clear nonce before any later trusted click',async()=>{
  for(const mode of ['cancel','escape']){
    const p=await panel({official:true,inventory:detectedInventory()});
    await p.invoke('start_fm1_official_update_review',{});
    if(mode==='cancel')p.node('cancel').onclick();else p.node('approval').cancel();
    p.node('confirm').onclick({isTrusted:true});await tick();
    assert.ok(!p.requests.includes('confirm_fm1_official_update'));
    assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM official_update_approvals').get().used,0);
    p.dispose();
  }
});

test('native official review uses host-private approval metadata and trusted confirmation',async()=>{
  const p=await panel({embedded:true,official:true,inventory:detectedInventory('ota_sysex')});
  assert.equal(p.registered.size,0);assert.equal(p.node('official-update').disabled,false);
  p.node('official-update').onclick();await tick();
  assert.equal(p.node('approval').open,true);
  const id=p.env.DB.sqlite.prepare('SELECT id FROM official_update_approvals').get().id;
  assert.ok(!p.node('review').innerHTML.includes(id));
  p.node('confirm').onclick({isTrusted:false});await tick();
  assert.ok(!p.requests.includes('confirm_fm1_official_update'));
  p.node('confirm').onclick({isTrusted:true});await tick();
  assert.equal(p.requestArgs.find(item=>item.name==='confirm_fm1_official_update').args.approval_id,id);
  assert.equal(p.node('job-id').value,id);
  assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM official_update_approvals').get().used,1);
  p.dispose();
});

test('official lost response retains exact job identity and inspection never opens another updater',async()=>{
  for(const embedded of [false,true]){
    const p=await panel({embedded,official:true,inventory:detectedInventory(),loseConfirmationReply:true});
    if(embedded){p.node('official-update').onclick();await tick();}else await p.invoke('start_fm1_official_update_review',{});
    const id=p.env.DB.sqlite.prepare('SELECT id FROM official_update_approvals').get().id;
    p.node('confirm').onclick({isTrusted:true});await tick();
    assert.equal(p.node('job-id').value,id);assert.match(p.node('message').textContent,/Inspect job/);
    assert.match(p.node('message').textContent,new RegExp(id));
    assert.equal(p.env.DB.sqlite.prepare("SELECT count(*) AS n FROM relay_tasks WHERE operation='official_updater'").get().n,1);
    p.node('inspect').onclick();await tick();
    assert.equal(p.requestArgs.find(item=>item.name==='get_fm1_job').args.job_id,id);
    assert.equal(p.requests.filter(name=>name==='confirm_fm1_official_update').length,1);
    assert.match(p.node('detail').textContent,new RegExp(id));
    p.dispose();
  }
});

test('native update mode and official button reflect recognized MIDI and independent capability',async()=>{
  const labels={serial:'Serial USB → UBOOT',uboot:'UBOOT',sysex:'MIDI / SysEx',ota_sysex:'MIDI / OTA',
    ambiguous:'Multiple candidates',unknown:'Unrecognized',disconnected:'Disconnected'};
  for(const [mode,label] of Object.entries(labels)){
    const p=await panel({embedded:true,official:true,inventory:detectedInventory(mode)});
    assert.equal(p.node('update-mode').textContent,label);
    assert.equal(p.node('official-update').disabled,!['sysex','ota_sysex'].includes(mode));
    assert.equal(p.requests.length,0);p.dispose();
  }
  const p=await panel({embedded:true,official:false,inventory:detectedInventory()});
  assert.equal(p.node('official-update').disabled,true);assert.equal(p.node('official-state').textContent,'Disabled');
  p.dispose();
});

test('busy and persistent engine latches disable official button despite available updater metadata',async()=>{
  for(const engine of [{active:'saved-job'},{blocked_unknown:true},{storage_fault:true},{updater_handoff:true}]){
    const inventory=detectedInventory();Object.assign(inventory.engine,engine);
    const p=await panel({embedded:true,official:true,inventory});
    assert.equal(p.node('official-update').disabled,true);
    assert.equal(p.node('official-state').textContent,engine.updater_handoff?'Complete vendor update':'Resolve saved bench job');
    assert.equal(p.requests.length,0);p.dispose();
  }
});

test('replacing app review with official review confirms only latest displayed family and nonce',async()=>{
  const p=await panel({official:true,inventory:detectedInventory()});
  await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});
  const switchId=p.env.DB.sqlite.prepare('SELECT id FROM switch_approvals').get().id;
  await p.invoke('start_fm1_official_update_review',{});
  const officialId=p.env.DB.sqlite.prepare('SELECT id FROM official_update_approvals').get().id;
  p.node('confirm').onclick({isTrusted:true});await tick();
  assert.ok(!p.requests.includes('confirm_fm1_switch'));
  assert.equal(p.requestArgs.find(item=>item.name==='confirm_fm1_official_update').args.approval_id,officialId);
  assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM switch_approvals WHERE id=?').get(switchId).used,0);
  assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM official_update_approvals WHERE id=?').get(officialId).used,1);
  p.dispose();
});

test('auto WebMCP switch review shows detected route and never queues before human confirmation',async()=>{
  const p=await panel({inventory:detectedInventory('uboot')});
  const result=await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'auto'});
  assert.equal(result.review.entry_method,'auto');assert.equal(result.review.detected_method,'already_uboot');
  assert.match(p.node('review').innerHTML,/auto → already_uboot/);
  assert.equal(p.env.DB.sqlite.prepare("SELECT count(*) AS n FROM relay_tasks WHERE operation='switch_app'").get().n,0);
  p.dispose();
});

test('native teardown clears a staged official approval before any later trusted click',async()=>{
  const p=await panel({embedded:true,official:true,inventory:detectedInventory()});
  p.node('official-update').onclick();await tick();
  p.events.get('message')({source:p.parent,data:{jsonrpc:'2.0',id:92,method:'ui/resource-teardown',params:{}}});await tick();
  p.node('confirm').onclick({isTrusted:true});await tick();
  assert.ok(!p.requests.includes('confirm_fm1_official_update'));
  assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM official_update_approvals').get().used,0);
  p.dispose();
});

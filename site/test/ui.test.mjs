import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { UI_HTML } from '../lib/fm1-ui.mjs';
import { callTool } from '../lib/fm1-server.mjs';
import { database, connect, cacheCatalog } from './d1.mjs';

const tick=()=>new Promise(resolve=>setTimeout(resolve,15));
async function panel({embedded=false,initial=true,serverTools=true,inventory=null}={}){
  const env=database();connect(env);cacheCatalog(env);
  const nodes=new Map(),registered=new Map(),requests=[],events=new Map(),notifications=[];
  function node(id){if(!nodes.has(id))nodes.set(id,{textContent:'',innerHTML:'',value:'',hidden:true,open:false,style:{},querySelectorAll:()=>[],querySelector:()=>null,removeAttribute(){},showModal(){this.open=true;},close(){this.open=false;},addEventListener(name,fn){this[name]=fn;}});return nodes.get(id);}
  const initialData=await callTool(env,'alice','open_fm1_library',{});
  if(inventory)initialData.inventory=inventory;
  const window={addEventListener(name,fn,options){events.set(name,fn);options?.signal?.addEventListener('abort',()=>events.delete(name));},removeEventListener(name){events.delete(name);}};
  const parent=embedded?{postMessage(message){notifications.push(message);if(message.id===undefined||!message.method)return;queueMicrotask(async()=>{
    const result=message.method==='ui/initialize'?{protocolVersion:'2026-01-26',hostInfo:{name:'FM1 fixture host',version:'1'},hostCapabilities:serverTools?{serverTools:{}}:{},hostContext:{theme:'dark',displayMode:'fullscreen'}}:{content:[],structuredContent:await backend(message.params.name,message.params.arguments)};
    events.get('message')?.({source:parent,data:{jsonrpc:'2.0',id:message.id,result}});
    if(message.method==='ui/initialize'&&initial)events.get('message')?.({source:parent,data:{jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{content:[],structuredContent:initialData}}});
  });}}:window;
  window.parent=parent;
  async function backend(name,args){requests.push(name);const answer=await callTool(env,'alice',name,args);if(answer.request_id){env.DB.sqlite.prepare('UPDATE relay_tasks SET state=?,result=? WHERE id=?').run('succeeded',JSON.stringify({status:'succeeded',data:{id:answer.job_id||answer.request_id,status:'succeeded',simulation:true}}),answer.request_id);}return answer;}
  const document={body:{classList:{add(){}},dataset:{}},getElementById:node,modelContext:{async registerTool(tool,{signal}){registered.set(tool.name,tool);signal.addEventListener('abort',()=>registered.delete(tool.name));}}};
  const context=vm.createContext({document,window,AbortController,Map,Object,Number,JSON,RegExp,String,Error,URL,TextEncoder,TextDecoder,crypto,queueMicrotask,setTimeout:(fn,ms)=>setTimeout(fn,ms>=10000?500:1),clearTimeout,fetch:async(_url,options)=>{const input=JSON.parse(options.body);try{return {ok:true,json:async()=>({structuredContent:await backend(input.name,input.arguments)})};}catch(error){return {ok:false,json:async()=>({error:error.message})};}}});
  for(const script of UI_HTML.matchAll(/<script>([\s\S]*?)<\/script>/g))vm.runInContext(script[1],context);
  await tick();
  return {env,nodes,registered,requests,events,notifications,parent,window,node,async invoke(name,args){return registered.get(name).execute(args);},dispose(){events.get('pagehide')?.();}};
}
test('host initial tool result renders without a duplicate library request',async()=>{const p=await panel({embedded:true});assert.equal(p.node('relay-state').textContent,'Connected');assert.equal(p.requests.length,0);assert.equal(p.registered.size,0);p.dispose();});
test('initial host result renders even without serverTools capability',async()=>{const p=await panel({embedded:true,serverTools:false});assert.equal(p.node('relay-state').textContent,'Connected');assert.equal(p.requests.length,0);p.dispose();});
test('native plugin opens on device controls with detected port and no duplicate refresh',async()=>{const p=await panel({embedded:true,inventory:{device:{serial_ports:[{port:'COM7'}],session_configured:false},engine:{active:null,blocked_unknown:false}}});assert.equal(p.node('surface-label').textContent,'FM1 plugin');assert.equal(p.node('device-heading').textContent,'FM1 on COM7');assert.equal(p.node('physical-device').textContent,'FM1 on COM7');assert.equal(p.requests.length,0);p.dispose();});
test('host with serverTools falls back once if initial result absent',async()=>{const p=await panel({embedded:true,initial:false});assert.deepEqual(p.requests,['open_fm1_library']);p.dispose();});
test('resource teardown is acknowledged and aborts the panel lifecycle',async()=>{const p=await panel({embedded:true});p.events.get('message')({source:p.parent,data:{jsonrpc:'2.0',id:91,method:'ui/resource-teardown',params:{}}});await tick();const ack=p.notifications.find(m=>m.id===91);assert.deepEqual(JSON.parse(JSON.stringify(ack)),{jsonrpc:'2.0',id:91,result:{}});const n=p.requests.length;p.node('refresh').onclick();await tick();assert.equal(p.requests.length,n);p.dispose();});
test('top-level document registers six tools and abort removes them',async()=>{const p=await panel();assert.equal(p.registered.size,6);assert.ok(!p.registered.has('confirm_fm1_switch'));p.dispose();assert.equal(p.registered.size,0);});
test('WebMCP review opens a dialog without exposing approval or submitting write',async()=>{const p=await panel();const reviewed=await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});assert.equal(p.node('approval').open,true);assert.ok(!('_approval' in reviewed));const nonce=p.env.DB.sqlite.prepare('SELECT id FROM switch_approvals').get().id;assert.ok(!JSON.stringify(reviewed).includes(nonce));assert.ok(!p.requests.includes('confirm_fm1_switch'));p.dispose();});
test('programmatic confirmation cannot consume the approval',async()=>{const p=await panel();await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});p.node('confirm').onclick({isTrusted:false});await tick();assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM switch_approvals').get().used,0);assert.equal(p.node('approval').open,true);p.dispose();});
test('cancel and Escape clear approval before any later click',async()=>{for(const mode of ['cancel','escape']){const p=await panel();await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});if(mode==='cancel')p.node('cancel').onclick();else p.node('approval').cancel();p.node('confirm').onclick({isTrusted:true});await tick();assert.ok(!p.requests.includes('confirm_fm1_switch'));p.dispose();}});
test('trusted confirmation uses the displayed approval once',async()=>{const p=await panel();await p.invoke('start_fm1_switch_review',{catalog_id:'nes-test',entry_method:'serial'});p.node('confirm').onclick({isTrusted:true});p.node('confirm').onclick({isTrusted:true});await tick();assert.equal(p.requests.filter(name=>name==='confirm_fm1_switch').length,1);assert.equal(p.env.DB.sqlite.prepare('SELECT used FROM switch_approvals').get().used,1);p.dispose();});
test('Inspect job awaits queued response and displays authoritative result',async()=>{const p=await panel();p.node('job-id').value='e'.repeat(32);p.node('inspect').onclick();await tick();assert.ok(p.requests.includes('get_fm1_request'));assert.match(p.node('detail').textContent,/succeeded/);p.dispose();});
test('every browser tool rejects malformed arguments without backend call',async()=>{const p=await panel();const n=p.requests.length;for(const tool of p.registered.values())await assert.rejects(tool.execute({unexpected:'x'}),/arguments/);await assert.rejects(p.invoke('plan_fm1_app',{catalog_id:'Bad-ID'}),/Invalid/);assert.equal(p.requests.length,n);p.dispose();});

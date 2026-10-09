import test from 'node:test';
import assert from 'node:assert/strict';
import { Client, StreamableHTTPClientTransport } from '@modelcontextprotocol/client';
import { handleFm1Request } from '../lib/fm1-server.mjs';
import { RESOURCE_URI } from '../lib/fm1-contract.mjs';
import { database } from './d1.mjs';

for(const [era,revision] of [['modern','2026-07-28'],['legacy','2025-11-25']]){
  test('real SDK '+era+' client discovers and uses the same private FM1 plugin',async()=>{
    const env=database(),requests=[];
    const client=new Client({name:'FM1 compatibility test',version:'2.0.0'},{capabilities:{},
      versionNegotiation:{mode:era==='modern'?{pin:revision}:'legacy'},supportedProtocolVersions:[revision]});
    const transport=new StreamableHTTPClientTransport(new URL('https://fm1.test/mcp'),{
      requestInit:{headers:{'oai-authenticated-user-id':'alice'}},
      fetch:async(input,init)=>{const request=new Request(input,init);if(request.method==='POST')requests.push(await request.clone().json());return handleFm1Request(request,env);},
    });
    try{
      await client.connect(transport);
      assert.equal(client.getProtocolEra(),era);
      assert.equal(client.getNegotiatedProtocolVersion(),revision);
      const tools=await client.listTools();
      assert.equal(tools.tools.length,8);
      const panel=tools.tools.find(tool=>tool.name==='open_fm1_library');
      assert.equal(panel._meta.ui.resourceUri,RESOURCE_URI);
      assert.deepEqual(panel._meta['openai/ui'].entrypoints,[{type:'global'},{type:'thread'}]);
      assert.deepEqual(tools.tools.find(tool=>tool.name==='confirm_fm1_switch')._meta.ui.visibility,['app']);
      const resource=await client.readResource({uri:RESOURCE_URI});
      assert.equal(resource.contents[0].mimeType,'text/html;profile=mcp-app');
      assert.match(resource.contents[0].text,/FM1PluginHost/);
      const library=await client.callTool({name:'open_fm1_library',arguments:{}});
      assert.equal(library.structuredContent.profiles.length,5);
      assert.equal(library.structuredContent.relay.connected,false);
      assert.equal(env.DB.sqlite.prepare('SELECT count(*) AS n FROM relay_tasks').get().n,0);
      const invalid=await client.callTool({name:'plan_fm1_app',arguments:{catalog_id:'../bad'}});
      assert.equal(invalid.isError,true);
      assert.equal(env.DB.sqlite.prepare('SELECT count(*) AS n FROM relay_tasks').get().n,0);
      assert.equal(requests.some(r=>r.method==='server/discover'),era==='modern');
      assert.equal(requests.some(r=>r.method==='initialize'),era==='legacy');
    }finally{await client.close();}
  });
}

const meta=(revision='2026-07-28')=>({
  'io.modelcontextprotocol/protocolVersion':revision,
  'io.modelcontextprotocol/clientCapabilities':{},
  'io.modelcontextprotocol/clientInfo':{name:'FM1 wire test',version:'2.0.0'},
});
async function modern(method,params={},extraHeaders={}){
  const response=await handleFm1Request(new Request('https://fm1.test/mcp',{method:'POST',
    headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream',
      'MCP-Protocol-Version':params._meta?.['io.modelcontextprotocol/protocolVersion']||'2026-07-28',
      'Mcp-Method':method,...(params.name?{'Mcp-Name':params.name}:{}),...extraHeaders},
    body:JSON.stringify({jsonrpc:'2.0',id:8,method,params}),
  }),database());
  return {status:response.status,value:await response.json(),headers:response.headers};
}
test('modern discovery has typed result, identity and private cache semantics',async()=>{
  const {status,value}=await modern('server/discover',{_meta:meta()});
  assert.equal(status,200);assert.equal(value.result.resultType,'complete');
  assert.ok(value.result.supportedVersions.includes('2026-07-28'));
  assert.equal(value.result._meta['io.modelcontextprotocol/serverInfo'].version,'2.0.0');
  assert.equal(value.result.ttlMs,0);assert.equal(value.result.cacheScope,'private');
});
test('modern missing envelope, unsupported revision and mismatched routing header reject before work',async()=>{
  const missing=await modern('server/discover',{});assert.equal(missing.status,400);assert.equal(missing.value.error.code,-32602);
  const version=await modern('server/discover',{_meta:meta('2099-01-01')});assert.equal(version.status,400);assert.equal(version.value.error.code,-32022);
  const route=await modern('server/discover',{_meta:meta()},{'Mcp-Method':'tools/list'});assert.equal(route.status,400);assert.equal(route.value.error.code,-32020);
});

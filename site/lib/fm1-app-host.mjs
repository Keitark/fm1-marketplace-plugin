import { App } from '@modelcontextprotocol/ext-apps';

// Bundled into the UI resource; no CDN or cross-origin browser request is used.
window.FM1PluginHost = class {
  constructor({onToolResult,onTeardown,onContext}) {
    this.app=new App({name:'FM1 Forge',version:'3.0.0'},
      {availableDisplayModes:['inline','fullscreen']},{autoResize:false});
    this.app.addEventListener('toolresult',onToolResult);
    this.app.addEventListener('hostcontextchanged',onContext);
    this.app.onteardown=async()=>{onTeardown();return {};};
  }
  async connect() {
    await this.app.connect();
    return {capabilities:this.app.getHostCapabilities()||{},context:this.app.getHostContext()||{}};
  }
  call(name,args,signal) {return this.app.callServerTool({name,arguments:args},{signal,timeout:15000});}
  async message(text,signal) {
    if(!this.app.getHostCapabilities()?.message?.text)throw new Error('This host does not support panel messages. Copy the project prompt into Codex.');
    const result=await this.app.sendMessage({role:'user',content:[{type:'text',text}]},{signal,timeout:15000});
    if(result.isError)throw new Error('The host rejected the project request. Copy the prompt into Codex.');
    return result;
  }
  close() {void this.app.close();}
};

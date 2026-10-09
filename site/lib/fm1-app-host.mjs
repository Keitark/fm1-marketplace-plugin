import { App } from '@modelcontextprotocol/ext-apps';

// Bundled into the UI resource; no CDN or cross-origin browser request is used.
window.FM1PluginHost = class {
  constructor({onToolResult,onTeardown,onContext}) {
    this.app=new App({name:'FM1 device panel',version:'2.0.0'},
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
  close() {void this.app.close();}
};

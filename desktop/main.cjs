const {app,BrowserWindow,ipcMain,session}=require('electron');
const path=require('node:path');
const origin=process.env.PAWGRESS_URL||'http://127.0.0.1:8000';
const parsed=new URL(origin);
if(!['https:','http:'].includes(parsed.protocol)|| (parsed.protocol==='http:'&&!['127.0.0.1','localhost'].includes(parsed.hostname)))throw Error('Use HTTPS or a loopback backend.');
let planner,companion;
function createWindow(options){
 const win=new BrowserWindow({...options,icon:path.join(__dirname,'../app/static/assets/logo.png'),webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,partition:'persist:Pawgress'}});
 win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
 win.webContents.on('will-navigate',(event,url)=>{if(new URL(url).origin!==parsed.origin)event.preventDefault();});
 win.webContents.on('will-attach-webview',event=>event.preventDefault());
 return win;
}
function showPlanner(){if(planner&&!planner.isDestroyed()){planner.show();planner.focus();return;}planner=createWindow({width:1280,height:850,minWidth:700,minHeight:550,title:'Pawgress',backgroundColor:'#f5f9f8'});planner.loadURL(parsed.origin);}
app.whenReady().then(()=>{
 session.fromPartition('persist:Pawgress').setPermissionRequestHandler((_contents,_permission,callback)=>callback(false));
 showPlanner();
 ipcMain.on('Pawgress:companion',(event,id)=>{if(new URL(event.senderFrame.url).origin!==parsed.origin)return;if(typeof id!=='string'||!/^[a-zA-Z0-9-]{1,100}$/.test(id))return;if(companion&&!companion.isDestroyed())companion.close();companion=createWindow({width:410,height:760,minWidth:340,minHeight:500,alwaysOnTop:true,title:'Pawgress companion',backgroundColor:'#f5f9f8',autoHideMenuBar:true});companion.loadURL(parsed.origin+'/companion?project='+encodeURIComponent(id));});
 ipcMain.on('Pawgress:planner',event=>{if(new URL(event.senderFrame.url).origin===parsed.origin)showPlanner();});
 app.on('activate',showPlanner);
});
app.on('window-all-closed',()=>app.quit());

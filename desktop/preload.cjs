const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('PawgressDesktop',Object.freeze({openCompanion:id=>ipcRenderer.send('Pawgress:companion',id),openPlanner:()=>ipcRenderer.send('Pawgress:planner')}));

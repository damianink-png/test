import { invoke,convertFileSrc,isTauri } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';
import type { Job,Settings } from './model';
export const native=isTauri();
export async function call<T>(command:string,args:Record<string,unknown>={}):Promise<T>{if(!native)throw Error('Ta funkcja wymaga aplikacji desktopowej. Podgląd WWW nie uruchamia silnika CAD.');return invoke<T>(command,args);}
export async function pick(directory=false,multiple=false):Promise<string[]>{if(!native)throw Error('Wybór plików jest dostępny w aplikacji desktopowej.');const result=await open({directory,multiple,filters:directory?undefined:[{name:'Modele STEP',extensions:['step','stp']}]});return result?Array.isArray(result)?result:[result]:[];}
export const start=(mode:string,files:string[],settings:Settings)=>call<Job>('start_job',{request:{mode,files,settings}});
export const asset=(path:string)=>convertFileSrc(path);

export type DropEvent={type:string;paths?:string[];position?:{x:number;y:number}};
export async function watchDrops(handler:(event:DropEvent)=>void){if(!native)return ()=>{};const {getCurrentWebview}=await import('@tauri-apps/api/webview');return getCurrentWebview().onDragDropEvent(e=>handler(e.payload));}

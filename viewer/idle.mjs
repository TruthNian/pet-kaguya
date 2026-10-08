import {durations} from './clock.mjs';
import {idleSlot,idlePoseOffset} from './idle-clock.mjs';

const el=id=>document.getElementById(id);
const canvases=[el('idle-reference'),el('idle-animated')];
const contexts=canvases.map(c=>c.getContext('2d',{alpha:true}));
const media=matchMedia('(prefers-reduced-motion: reduce)');
el('idle-reduced').checked=media.matches;
let image=null,ready=false,timer=null,baseElapsed=0,startedAt=null,paused=false,manualIndex=null,lastIndex=-1,paintCount=0;
const reduced=()=>el('idle-reduced').checked;
const elapsed=()=>baseElapsed+(startedAt===null?0:performance.now()-startedAt);
const canRun=()=>ready&&!paused&&!reduced()&&!document.hidden;

function stopClock(){
  if(startedAt!==null){baseElapsed+=performance.now()-startedAt;startedAt=null;}
  if(timer!==null){clearTimeout(timer);timer=null;}
}
function size(){
  const width=Number(el('idle-size').value);
  for(const canvas of canvases){canvas.style.width=`${width}px`;canvas.style.height=`${Math.round(width*208/192)}px`;}
}
function draw(){
  if(!ready)return;
  const slot=idleSlot(elapsed());
  const index=manualIndex??(reduced()?0:slot.index);
  if(index!==lastIndex){
    const context=contexts[1];context.clearRect(0,0,192,208);context.imageSmoothingEnabled=false;
    context.drawImage(image,index*192,0,192,208,0,0,192,208);
    lastIndex=index;paintCount++;
  }
  el('idle-frame').value=String(index);
  el('idle-pause').disabled=reduced();
  el('idle-pause').textContent=paused?'播放 idle':'暂停 idle';
  el('idle-status').textContent=`${manualIndex!==null?'单帧检查':reduced()?'减少动态':paused?'已暂停':'实际时长播放'} · 第 ${index+1}/6 帧 · 停留 ${durations[0][index]} ms · 周期 6600 ms · ${paintCount} 次候选绘制 · 非完整宠物，未安装`;
}
function schedule(){
  if(!canRun())return;
  if(startedAt===null)startedAt=performance.now();
  if(timer!==null)clearTimeout(timer);
  timer=setTimeout(()=>{timer=null;draw();schedule();},Math.max(1,idleSlot(elapsed()).untilNext+.5));
}
el('idle-pause').addEventListener('click',()=>{stopClock();paused=!paused;manualIndex=null;draw();schedule();});
el('idle-restart').addEventListener('click',()=>{stopClock();baseElapsed=0;manualIndex=null;paused=false;draw();schedule();});
el('idle-frame').addEventListener('input',()=>{stopClock();paused=true;manualIndex=Number(el('idle-frame').value);baseElapsed=idlePoseOffset(manualIndex);draw();});
el('idle-size').addEventListener('change',size);
el('idle-background').addEventListener('change',()=>{el('idle-stage').className=`stage ${el('idle-background').value}`;});
el('idle-reduced').addEventListener('change',()=>{stopClock();manualIndex=null;draw();schedule();});
media.addEventListener('change',event=>{stopClock();el('idle-reduced').checked=event.matches;manualIndex=null;draw();schedule();});
document.addEventListener('visibilitychange',()=>{stopClock();draw();schedule();});
window.addEventListener('pagehide',stopClock);
try{
  const response=await fetch('../candidates/phase5/idle/build.json');
  if(!response.ok)throw new Error('Idle build metadata unavailable');
  const metadata=await response.json();
  if(metadata.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
      ||metadata.facialGeometryRepair!==false||JSON.stringify(metadata.durationsMs)!==JSON.stringify(durations[0]))
    throw new Error('Idle source or native schedule mismatch');
  image=new Image();image.src='../candidates/phase5/idle/strip.webp';await image.decode();
  if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('Idle strip dimensions mismatch');
  contexts[0].imageSmoothingEnabled=false;contexts[0].drawImage(image,0,0,192,208,0,0,192,208);
  ready=true;size();draw();schedule();
}catch(error){el('idle-status').textContent=`Idle 加载失败：${error.message}`;console.error(error);}

import {reviewSchedule} from './whole-review-clock.mjs';
import {paintCel} from './cel-painter.mjs';

const el=id=>document.getElementById(id);
const steps=reviewSchedule(),contexts=[...document.querySelectorAll('canvas')].map(c=>c.getContext('2d',{alpha:true}));
const total=steps.reduce((n,step)=>n+step.holdMs,0),prefix=[];
steps.reduce((n,step)=>{prefix.push(n);return n+step.holdMs;},0);
let atlas,position=0,timer=null,playing=false,deadline=0,remaining=steps[0].holdMs,lastKey;
function cancel(){if(timer!==null)clearTimeout(timer);timer=null;}
function draw(){
  const step=steps[position],key=`${step.row}:${step.index}`;
  if(key!==lastKey){contexts.forEach(context=>paintCel(context,atlas,step.index,step.row));lastKey=key;}
  el('chapter').value=step.chapter;
  el('state').textContent=step.state==='look'?`视线 ${step.direction+1}/16 · 只移动原虹膜`
    :step.after?`回到 idle · ${step.after==='look'?'视线演示':step.after+'三轮'}结束`
    :`${step.state} · 第${step.index+1}格${step.row===0?'':` · 第${step.cycle}/3轮`}`;
  el('progress').value=prefix[position]/total;
  el('status').textContent=`${playing?'播放中':'已暂停'} · 本格${step.holdMs}ms${step.state==='look'?'（演示设置）':'（原生计划）'} · 两尺寸×明暗同格 · 无补间 · 未安装`;
  el('pause').textContent=playing?'暂停演示':'播放演示';
}
function schedule(){
  deadline=performance.now()+remaining;
  timer=setTimeout(()=>{
    timer=null;
    if(position===steps.length-1){playing=false;remaining=steps[position].holdMs;draw();el('progress').value=1;el('status').textContent='完整观看结束 · 图集/安装未改变 · 手袖、切换及整体自然度仍待判断';return;}
    position++;remaining=steps[position].holdMs;draw();schedule();
  },remaining);
}
function stop(){if(playing){remaining=Math.max(0,deadline-performance.now());playing=false;cancel();draw();}}
function start(){if(document.hidden)return;playing=true;draw();schedule();}
el('pause').addEventListener('click',()=>playing?stop():start());
el('replay').addEventListener('click',()=>{cancel();position=0;remaining=steps[0].holdMs;playing=false;start();});
el('chapter').addEventListener('change',()=>{cancel();position=steps.findIndex(step=>step.chapter===el('chapter').value);remaining=steps[position].holdMs;draw();if(playing)schedule();});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
addEventListener('pagehide',()=>stop());
try{
  const base='../candidates/phase5/global/';
  const metadata=await (await fetch(base+'build.json',{cache:'no-store'})).json();
  if(metadata.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
      ||metadata.visualAcceptance!=='pending'||metadata.installed!==false||metadata.generatedFromRejectedSources!==false
      ||metadata.cell.join(',')!=='192,208'||metadata.directionCount!==16)
    throw new Error('现用图集来源或开发边界不符');
  atlas=await createImageBitmap(await (await fetch(base+'spritesheet.webp',{cache:'no-store'})).blob());
  if(atlas.width!==1536||atlas.height!==2288)throw new Error('原生图集尺寸不符');
  draw();['replay','pause','chapter'].forEach(id=>el(id).disabled=false);
}catch(error){cancel();playing=false;el('state').textContent='无法载入现用图集';el('status').textContent=error.message;}

// Static native look cells. No timer/interpolation/body motion or host patch.
import {gazeFrame,pointerGaze} from './gaze-frame.mjs';
const el=id=>document.getElementById(id);
const reference=el('gaze-reference'),pet=el('gaze-pet');
const contexts=[reference,pet].map(c=>c.getContext('2d',{alpha:true}));
let ready=false,loading=null,strip,neutral,index=null,lastKey='',drawCount=0;
function size(){
  const width=Number(el('gaze-size').value);
  for(const canvas of [reference,pet]){canvas.style.width=`${width}px`;canvas.style.height=`${Math.round(width*208/192)}px`;}
}
function draw(){
  if(!ready)return;
  const cell=gazeFrame(index),key=String(index);
  if(key!==lastKey){
    contexts[1].clearRect(0,0,192,208);contexts[1].imageSmoothingEnabled=false;
    contexts[1].drawImage(cell.neutral?neutral:strip,cell.x,cell.y,192,208,0,0,192,208);
    lastKey=key;drawCount++;
  }
  el('gaze-direction').value=index===null?'neutral':String(index);
  el('gaze-status').textContent=`${cell.neutral?'原图中性视线':`方向 ${index} · ${index*22.5}° · 原生行 ${cell.row} / 列 ${cell.col}`} · ${drawCount} 次候选绘制 · 仅眼内变化，无全身旋转/镜像/补间 · 视觉待验收，非完整宠物，未安装`;
}
async function load(){
  if(ready||loading)return loading;
  loading=(async()=>{
    try{
      const root='../candidates/phase5/look';
      const response=await fetch(`${root}/build.json`);
      if(!response.ok)throw new Error('gaze metadata unavailable');
      const metadata=await response.json();
      if(metadata.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
          ||metadata.directionCount!==16||JSON.stringify(metadata.nativeRows)!=='[9,10]'
          ||metadata.bodyRotated!==false||metadata.artMirrored!==false||metadata.irisShapeWarp!==false
          ||metadata.facialGeometryRepair!==false||metadata.eyeOutlineFixed!==true
          ||metadata.installableFullAtlas!==false||metadata.installed!==false)
        throw new Error('gaze source/shape/candidate boundary mismatch');
      strip=new Image();strip.src=`${root}/strip.webp`;
      neutral=new Image();neutral.src=`${root}/neutral.png`;
      await Promise.all([strip.decode(),neutral.decode()]);
      if(strip.naturalWidth!==1536||strip.naturalHeight!==416||neutral.naturalWidth!==192||neutral.naturalHeight!==208)
        throw new Error('gaze cell dimensions mismatch');
      contexts[0].imageSmoothingEnabled=false;contexts[0].drawImage(neutral,0,0);
      ready=true;size();draw();
    }catch(error){el('gaze-status').textContent=`视线候选加载失败：${error.message}`;console.error(error);loading=null;}
  })();
  return loading;
}
el('gaze-review').addEventListener('toggle',()=>{if(el('gaze-review').open)load();});
el('gaze-direction').addEventListener('change',()=>{
  index=el('gaze-direction').value==='neutral'?null:Number(el('gaze-direction').value);
  el('gaze-pointer').checked=false;draw();
});
el('gaze-size').addEventListener('change',size);
el('gaze-background').addEventListener('change',()=>{el('gaze-stage').className=`stage ${el('gaze-background').value}`;});
el('gaze-stage').addEventListener('pointermove',event=>{
  if(!ready||!el('gaze-pointer').checked)return;
  const bounds=pet.getBoundingClientRect();
  index=pointerGaze(event.clientX-(bounds.left+bounds.width/2),event.clientY-(bounds.top+bounds.height/2));
  draw();
});
el('gaze-stage').addEventListener('pointerleave',()=>{if(ready&&el('gaze-pointer').checked){index=null;draw();}});
if(el('gaze-review').open)await load();

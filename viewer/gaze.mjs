// Static native look cells. No timer/interpolation/body motion or host patch.
import {gazeFrame,pointerGaze} from './gaze-frame.mjs';
import {validateGazeFamily} from './gaze-contract.mjs';
const el=id=>document.getElementById(id);
const reference=el('gaze-reference'),pet=el('gaze-pet');
const contexts=[reference,pet].map(c=>c.getContext('2d',{alpha:true}));
let ready=false,baseline,selectedAsset,index=null,lastKey='',drawCount=0,request=0,family='current';
const assets=new Map();
function size(){
  const width=Number(el('gaze-size').value);
  for(const canvas of [reference,pet]){canvas.style.width=`${width}px`;canvas.style.height=`${Math.round(width*208/192)}px`;}
}
function draw(){
  if(!ready)return;
  const cell=gazeFrame(index),referenceCell=gazeFrame(family==='surface'?index:null),key=`${family}:${index}`;
  if(key!==lastKey){
    for(const [i,asset,which] of [[0,baseline,referenceCell],[1,selectedAsset,cell]]){
      contexts[i].clearRect(0,0,192,208);contexts[i].imageSmoothingEnabled=false;
      contexts[i].drawImage(which.neutral?asset.neutral:asset.strip,which.x,which.y,192,208,0,0,192,208);
    }
    lastKey=key;drawCount++;
  }
  el('gaze-direction').value=index===null?'neutral':String(index);
  el('gaze-reference-title').textContent=family==='surface'?'左 · 采用前眼动（12/7源px）':'v3 · 原图中性视线';
  el('gaze-candidate-title').textContent='右 · 现用原图眼内变形（6/4源px，开发基础）';
  reference.setAttribute('aria-label',family==='surface'?'同方向采用前视线':'原图中性视线');
  el('gaze-status').textContent=`${cell.neutral?'原图中性视线':`方向 ${index} · ${index*22.5}° · 原生行 ${cell.row} / 列 ${cell.col}`} · ${drawCount} 次候选绘制 · 原图眼内纹理变形，已采用为开发基础；虹膜略有形变、幅度更小${family==='surface'?'，非单因素对照':''} · 无宿主补间；完整视觉待验收，未安装`;
}
async function asset(name){
  if(!assets.has(name))assets.set(name,(async()=>{
      const root=name==='rigid'?'../sources/reference/gaze-rigid-v2':'../candidates/phase5/look';
      const response=await fetch(`${root}/build.json`,{cache:'no-cache'});
      if(!response.ok)throw new Error('gaze metadata unavailable');
      const metadata=await response.json();
      validateGazeFamily(metadata,name);
      const strip=new Image();strip.src=`${root}/strip.webp?v=${metadata.frameHashes[0]}`;
      const neutral=new Image();neutral.src=`${root}/neutral.png?v=${metadata.neutralFrameHash}`;
      await Promise.all([strip.decode(),neutral.decode()]);
      if(strip.naturalWidth!==1536||strip.naturalHeight!==416||neutral.naturalWidth!==192||neutral.naturalHeight!==208)
        throw new Error('gaze cell dimensions mismatch');
      return {strip,neutral,metadata};
  })().catch(error=>{assets.delete(name);throw error;}));
  return assets.get(name);
}
async function load(){
  const ticket=++request,requested=el('gaze-method').value;ready=false;
  try{
    const [current,chosen]=await Promise.all([asset(requested==='surface'?'rigid':'current'),asset('current')]);
    if(ticket!==request)return;
    baseline=current;selectedAsset=chosen;family=requested;lastKey='';ready=true;size();draw();
  }catch(error){if(ticket===request)el('gaze-status').textContent=`视线候选加载失败：${error.message}`;console.error(error);}
}
el('gaze-review').addEventListener('toggle',()=>{if(el('gaze-review').open)load();});
el('gaze-method').addEventListener('change',load);
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

// A native RGBA cel replaces canvas contents; it must never accumulate alpha.
export function paintCel(context,image,index=0){
  if(!Number.isInteger(index)||index<0||index>=8)throw new RangeError('Invalid native cel');
  context.clearRect(0,0,192,208);
  context.imageSmoothingEnabled=false;
  context.drawImage(image,index*192,0,192,208,0,0,192,208);
}

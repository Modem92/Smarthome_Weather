'use strict';
/* Shared pure layout behavior. The server independently validates every save. */
(function(root) {
  const copy = value => JSON.parse(JSON.stringify(value));
  function arrange(items, pinned=null, compact=false, columns=12, rows=8, preserve=false) {
    const result=copy(items);
    if(result.reduce((a,w)=>a+w.w*w.h,0)>columns*rows)throw new Error('NO_SPACE');
    if(preserve && !compact) {
      for(let i=0;i<result.length;i++) {
        const a=result[i];
        if(a.x<0||a.y<0||a.w<1||a.h<1||a.x+a.w>columns||a.y+a.h>rows||result.slice(0,i).some(b=>a.x<b.x+b.w&&b.x<a.x+a.w&&a.y<b.y+b.h&&b.y<a.y+a.h))throw new Error('NO_SPACE');
      }
      return result;
    }
    const order=[...result].sort((a,b)=>Number(a.id!==pinned)-Number(b.id!==pinned)||b.w*b.h-a.w*a.h||a.y-b.y||a.x-b.x);
    let attempts=0; const failed=new Set();
    function solve(index,occupied) {
      if(++attempts>50000)return false;
      if(index===order.length)return true;
      const state=`${index}:${occupied}`;if(failed.has(state))return false;
      const item=order[index],positions=[];
      for(let y=0;y<=rows-item.h;y++)for(let x=0;x<=columns-item.w;x++)positions.push([x,y]);
      if(item.id===pinned || item.locked)positions.splice(0,positions.length,[item.x,item.y]);
      else if(!compact)positions.sort((a,b)=>Number(a[0]!==item.x||a[1]!==item.y)-Number(b[0]!==item.x||b[1]!==item.y)||Math.abs(a[0]-item.x)+Math.abs(a[1]-item.y)-Math.abs(b[0]-item.x)-Math.abs(b[1]-item.y)||a[1]-b[1]||a[0]-b[0]);
      for(const [x,y] of positions) {
        if(x<0||y<0||x+item.w>columns||y+item.h>rows)continue;
        let mask=0n;for(let r=y;r<y+item.h;r++)mask|=((1n<<BigInt(item.w))-1n)<<BigInt(r*columns+x);
        if(!(occupied&mask)){item.x=x;item.y=y;if(solve(index+1,occupied|mask))return true;}
      }
      failed.add(state);return false;
    }
    if(!solve(0,0n))throw new Error('NO_SPACE');return result;
  }
  root.WidgetLayout={copy,arrange};
})(globalThis);

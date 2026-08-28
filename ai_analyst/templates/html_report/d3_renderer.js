// ── HELPERS ──────────────────────────────────────────────────────────────────
function setupTooltip(el) {
  var tt = d3.select(el).select('.chart-tooltip');
  if (tt.empty()) tt = d3.select(el).append('div').attr('class','chart-tooltip');
  return tt;
}
function showTT(tt, ev, html) {
  tt.html(html).style('opacity',1);
  var n=tt.node(), pr=n.parentNode.getBoundingClientRect(), tr=n.getBoundingClientRect();
  var lx=ev.clientX-pr.left+14, ly=ev.clientY-pr.top-10;
  if(lx+tr.width>pr.width)  lx=ev.clientX-pr.left-tr.width-14;
  if(ly+tr.height>pr.height) ly=ev.clientY-pr.top-tr.height-10;
  tt.style('left',lx+'px').style('top',ly+'px');
}
function hideTT(tt) { tt.style('opacity',0); }
function fmtK(v) {
  if(v==null) return '';
  var a=Math.abs(v), s=v<0?'-':'';
  if(a>=1000) return s+'$'+d3.format(',.1f')(a/1000)+'K';
  return s+'$'+d3.format(',.0f')(a);
}
function mkSvg(el,W,H) {
  return d3.select(el).append('svg')
    .attr('viewBox','0 0 '+W+' '+H)
    .attr('width',W).attr('height',H)
    .attr('preserveAspectRatio','xMinYMin meet')
    .style('width','100%').style('height','auto');
}
function cleanAx(g) {
  g.selectAll('.domain').attr('stroke','#CBD5E1');
  g.selectAll('.tick line').attr('stroke','#CBD5E1');
  g.selectAll('.tick text').attr('fill','#64748B').attr('font-size',11);
}

// ── HIGHLIGHT LINE ────────────────────────────────────────────────────────────
function renderHighlightLine(el, spec) {
  var d=spec.data, lbls=d.labels||[], ser=(d.series||[])[0]||{};
  var vals=ser.values||[];
  if(!vals.length) return;
  var hiIdx=ser.highlight_indices||[], trIdx=ser.trough_indices||[];
  var cDef=ser.color_default||'#94A3B8', cHi=ser.color_highlight||'#2B4EFF', cTr=ser.color_trough||'#EF4444';
  var W=800,H=320,m={top:24,right:28,bottom:46,left:72};
  var w=W-m.left-m.right, hh=H-m.top-m.bottom;
  var svg=mkSvg(el,W,H), g=svg.append('g').attr('transform','translate('+m.left+','+m.top+')');
  var tt=setupTooltip(el);
  var xs=d3.scalePoint().domain(lbls).range([0,w]).padding(0.15);
  var yMax=d3.max(vals)*1.18||1;
  var ys=d3.scaleLinear().domain([0,yMax]).range([hh,0]);
  g.select('.domain').remove();
  // area
  var area=d3.area().x(function(_,i){return xs(lbls[i]);}).y0(hh).y1(function(v){return ys(v);}).curve(d3.curveMonotoneX).defined(function(v){return v!=null;});
  g.append('path').datum(vals).attr('fill',cHi+'18').attr('d',area);
  // line
  var line=d3.line().x(function(_,i){return xs(lbls[i]);}).y(function(v){return ys(v);}).curve(d3.curveMonotoneX).defined(function(v){return v!=null;});
  g.append('path').datum(vals).attr('fill','none').attr('stroke',cDef).attr('stroke-width',2.5).attr('d',line);
  // dots
  vals.forEach(function(v,i){
    if(v==null) return;
    var isTr=trIdx.indexOf(i)>=0, isHi=hiIdx.indexOf(i)>=0;
    var col=isTr?cTr:isHi?cHi:cDef, r=isTr||isHi?6:3.5;
    g.append('circle').attr('cx',xs(lbls[i])).attr('cy',ys(v)).attr('r',r)
      .attr('fill',col).attr('stroke','#fff').attr('stroke-width',1.5).style('cursor','pointer')
      .on('mouseover',function(ev){showTT(tt,ev,'<strong>'+lbls[i]+'</strong><br/>'+fmtK(v));})
      .on('mousemove',function(ev){showTT(tt,ev,'<strong>'+lbls[i]+'</strong><br/>'+fmtK(v));})
      .on('mouseout',function(){hideTT(tt);});
  });
  // axes
  var tickEvery=Math.max(1,Math.ceil(lbls.length/12));
  g.append('g').attr('transform','translate(0,'+hh+')').call(d3.axisBottom(xs).tickValues(lbls.filter(function(_,i){return i%tickEvery===0;})));
  g.append('g').call(d3.axisLeft(ys).ticks(5).tickFormat(fmtK));
  cleanAx(g);
}

// ── HIGHLIGHT BAR ─────────────────────────────────────────────────────────────
function renderHighlightBar(el, spec) {
  var d=spec.data, lbls=d.labels||[], ser=(d.series||[])[0]||{};
  var vals=ser.values||[], cols=ser.colors||[];
  if(!vals.length) return;
  var defCol='#2B4EFF';
  var W=800,H=300,m={top:20,right:20,bottom:60,left:72};
  var w=W-m.left-m.right, hh=H-m.top-m.bottom;
  var svg=mkSvg(el,W,H), g=svg.append('g').attr('transform','translate('+m.left+','+m.top+')');
  var tt=setupTooltip(el);
  var xs=d3.scaleBand().domain(lbls).range([0,w]).padding(0.28);
  var yMax=d3.max(vals)*1.2||1;
  var ys=d3.scaleLinear().domain([0,yMax]).range([hh,0]);
  g.select('.domain').remove();
  vals.forEach(function(v,i){
    var col=cols[i]||defCol;
    var bh=Math.max(0,hh-ys(v));
    g.append('rect').attr('x',xs(lbls[i])).attr('y',ys(v)).attr('width',xs.bandwidth()).attr('height',bh)
      .attr('fill',col).attr('rx',3).style('cursor','pointer')
      .on('mouseover',function(ev){showTT(tt,ev,'<strong>'+lbls[i]+'</strong><br/>'+fmtK(v));})
      .on('mousemove',function(ev){showTT(tt,ev,'<strong>'+lbls[i]+'</strong><br/>'+fmtK(v));})
      .on('mouseout',function(){hideTT(tt);});
    g.append('text').attr('x',xs(lbls[i])+xs.bandwidth()/2).attr('y',ys(v)-5)
      .attr('text-anchor','middle').attr('font-size',10).attr('fill',col).attr('font-weight','600').text(fmtK(v));
  });
  g.append('g').attr('transform','translate(0,'+hh+')').call(d3.axisBottom(xs).tickFormat(function(d){return d.length>10?d.slice(0,9)+'…':d;}));
  g.append('g').call(d3.axisLeft(ys).ticks(5).tickFormat(fmtK));
  cleanAx(g);
}

// ── GROUPED BAR ───────────────────────────────────────────────────────────────
function renderGroupedBar(el, spec) {
  var d=spec.data, lbls=d.labels||[], series=d.series||[];
  if(!lbls.length||!series.length) return;
  var palette=['#94A3B8','#2B4EFF','#10B981','#F97316'];
  var W=800,H=300,m={top:24,right:100,bottom:46,left:72};
  var w=W-m.left-m.right, hh=H-m.top-m.bottom;
  var svg=mkSvg(el,W,H), g=svg.append('g').attr('transform','translate('+m.left+','+m.top+')');
  var tt=setupTooltip(el);
  var x0=d3.scaleBand().domain(lbls).range([0,w]).paddingInner(0.25);
  var x1=d3.scaleBand().domain(series.map(function(s){return s.name;})).range([0,x0.bandwidth()]).padding(0.06);
  var allVals=series.flatMap(function(s){return s.values||[];}).filter(function(v){return v!=null;});
  var yMax=d3.max(allVals)*1.2||1;
  var ys=d3.scaleLinear().domain([0,yMax]).range([hh,0]);
  g.select('.domain').remove();
  lbls.forEach(function(lbl){
    var grp=g.append('g').attr('transform','translate('+x0(lbl)+',0)');
    series.forEach(function(s,si){
      var v=(s.values||[])[lbls.indexOf(lbl)];
      if(v==null) return;
      var col=s.color||palette[si]||'#CBD5E1';
      grp.append('rect').attr('x',x1(s.name)).attr('y',ys(v)).attr('width',x1.bandwidth()).attr('height',Math.max(0,hh-ys(v)))
        .attr('fill',col).attr('rx',3).style('cursor','pointer')
        .on('mouseover',function(ev){showTT(tt,ev,'<strong>'+lbl+' · '+s.name+'</strong><br/>'+fmtK(v));})
        .on('mousemove',function(ev){showTT(tt,ev,'<strong>'+lbl+' · '+s.name+'</strong><br/>'+fmtK(v));})
        .on('mouseout',function(){hideTT(tt);});
    });
  });
  // legend
  series.forEach(function(s,si){
    var col=s.color||palette[si]||'#CBD5E1';
    g.append('rect').attr('x',w+8).attr('y',si*18+4).attr('width',11).attr('height',11).attr('fill',col).attr('rx',2);
    g.append('text').attr('x',w+22).attr('y',si*18+12).attr('font-size',10).attr('fill','#374151').text(s.name);
  });
  g.append('g').attr('transform','translate(0,'+hh+')').call(d3.axisBottom(x0));
  g.append('g').call(d3.axisLeft(ys).ticks(5).tickFormat(fmtK));
  cleanAx(g);
}

// ── HORIZONTAL BAR ────────────────────────────────────────────────────────────
function renderHorizontalBar(el, spec) {
  var d=spec.data, lbls=d.labels||[], ser=(d.series||[])[0]||{};
  var vals=ser.values||[], cols=ser.colors||[];
  if(!vals.length) return;
  var defCol='#2B4EFF';
  var hasNeg=vals.some(function(v){return v<0;});
  var W=800, H=Math.max(180, lbls.length*52+70), m={top:16,right:90,bottom:36,left:190};
  var w=W-m.left-m.right, hh=H-m.top-m.bottom;
  var svg=mkSvg(el,W,H), g=svg.append('g').attr('transform','translate('+m.left+','+m.top+')');
  var tt=setupTooltip(el);
  var ext=d3.extent(vals);
  var xMin=hasNeg?Math.min(0,ext[0]*1.2):0;
  var xMax=Math.max(0,ext[1]*1.2)||1;
  var xs=d3.scaleLinear().domain([xMin,xMax]).range([0,w]);
  var ys=d3.scaleBand().domain(lbls).range([0,hh]).padding(0.28);
  if(hasNeg) g.append('line').attr('x1',xs(0)).attr('x2',xs(0)).attr('y1',0).attr('y2',hh).attr('stroke','#1A202C').attr('stroke-width',1).attr('stroke-dasharray','3,3');
  vals.forEach(function(v,i){
    var col=cols[i]||defCol;
    var x1=Math.min(xs(0),xs(v)), bw=Math.abs(xs(v)-xs(0));
    g.append('rect').attr('y',ys(lbls[i])).attr('x',x1).attr('height',ys.bandwidth()).attr('width',Math.max(1,bw))
      .attr('fill',col).attr('rx',3).style('cursor','pointer')
      .on('mouseover',function(ev){showTT(tt,ev,'<strong>'+lbls[i]+'</strong><br/>'+d3.format(',.1f')(v)+'%');})
      .on('mousemove',function(ev){showTT(tt,ev,'<strong>'+lbls[i]+'</strong><br/>'+d3.format(',.1f')(v)+'%');})
      .on('mouseout',function(){hideTT(tt);});
    var labelX=v>=0?xs(v)+5:xs(v)-5;
    var anchor=v>=0?'start':'end';
    g.append('text').attr('y',ys(lbls[i])+ys.bandwidth()/2+4).attr('x',labelX)
      .attr('font-size',11).attr('fill','#374151').attr('text-anchor',anchor)
      .text(d3.format(',.1f')(v)+'%');
  });
  g.append('g').call(d3.axisLeft(ys).tickSize(0)).select('.domain').remove();
  g.selectAll('.tick text').attr('font-size',11);
  g.append('g').attr('transform','translate(0,'+hh+')').call(d3.axisBottom(xs).ticks(5).tickFormat(function(v){return d3.format(',.0f')(v)+'%';}));
  cleanAx(g);
}

// ── WATERFALL ─────────────────────────────────────────────────────────────────
function renderWaterfall(el, spec) {
  var d=spec.data, lbls=d.labels||[], ser=(d.series||[])[0]||{};
  var vals=ser.values||[], types=ser.types||[], cols=ser.colors||[];
  if(!vals.length) return;
  var W=800,H=320,m={top:24,right:20,bottom:60,left:82};
  var w=W-m.left-m.right, hh=H-m.top-m.bottom;
  var svg=mkSvg(el,W,H), g=svg.append('g').attr('transform','translate('+m.left+','+m.top+')');
  var tt=setupTooltip(el);
  var bars=[], running=0;
  vals.forEach(function(v,i){
    var t=types[i]||'positive', col=cols[i]||(v>=0?'#10B981':'#EF4444');
    var start, height;
    if(t==='base'||t==='total') { start=0; height=v; }
    else if(v>=0) { start=running; height=v; }
    else { start=running+v; height=-v; }
    bars.push({label:lbls[i], val:v, start:start, height:height, type:t, color:col});
    if(t!=='total') running += v;
  });
  var allTops=bars.map(function(b){return b.start+b.height;});
  var yMax=d3.max(allTops)*1.18||1;
  var xs=d3.scaleBand().domain(lbls).range([0,w]).padding(0.28);
  var ys=d3.scaleLinear().domain([0,yMax]).range([hh,0]);
  g.select('.domain').remove();
  bars.forEach(function(b){
    var bx=xs(b.label), bw=xs.bandwidth(), by=ys(b.start+b.height), bh=Math.max(1,ys(b.start)-ys(b.start+b.height));
    g.append('rect').attr('x',bx).attr('y',by).attr('width',bw).attr('height',bh)
      .attr('fill',b.color).attr('rx',3).style('cursor','pointer')
      .on('mouseover',function(ev){showTT(tt,ev,'<strong>'+b.label+'</strong><br/>'+fmtK(b.val));})
      .on('mousemove',function(ev){showTT(tt,ev,'<strong>'+b.label+'</strong><br/>'+fmtK(b.val));})
      .on('mouseout',function(){hideTT(tt);});
    g.append('text').attr('x',bx+bw/2).attr('y',by-4).attr('text-anchor','middle').attr('font-size',10).attr('fill',b.color).attr('font-weight','600').text(fmtK(b.val));
  });
  for(var i=0;i<bars.length-1;i++){
    var b=bars[i], bn=bars[i+1];
    if(b.type!=='total') {
      var cy=ys(b.start+(b.val>=0?b.val:0)+(b.val<0?b.val:0));
      var x1=xs(b.label)+xs.bandwidth(), x2=xs(bn.label);
      g.append('line').attr('x1',x1).attr('x2',x2).attr('y1',ys(b.start+b.height)).attr('y2',ys(b.start+b.height))
        .attr('stroke','#94A3B8').attr('stroke-width',1).attr('stroke-dasharray','3,2');
    }
  }
  g.append('g').attr('transform','translate(0,'+hh+')').call(d3.axisBottom(xs).tickFormat(function(s){return s.length>12?s.slice(0,11)+'…':s;}));
  g.append('g').call(d3.axisLeft(ys).ticks(5).tickFormat(fmtK));
  cleanAx(g);
}

// ── SLOPEGRAPH ────────────────────────────────────────────────────────────────
function renderSlopegraph(el, spec) {
  var d=spec.data, entityLbls=d.labels||[], series=d.series||[], slopes=d.slopes||[];
  if(series.length<2) return;
  var s0=series[0], s1=series[1];
  var W=700,H=320,m={top:30,right:120,bottom:46,left:120};
  var w=W-m.left-m.right, hh=H-m.top-m.bottom;
  var svg=mkSvg(el,W,H), g=svg.append('g').attr('transform','translate('+m.left+','+m.top+')');
  var allVals=(s0.values||[]).concat(s1.values||[]).filter(function(v){return v!=null;});
  var yMin=d3.min(allVals)*0.88, yMax=d3.max(allVals)*1.12;
  var ys=d3.scaleLinear().domain([yMin,yMax]).range([hh,0]);
  g.append('text').attr('x',-10).attr('y',-12).attr('text-anchor','end').attr('font-size',11).attr('font-weight','600').attr('fill','#374151').text(s0.name||'Before');
  g.append('text').attr('x',w+10).attr('y',-12).attr('text-anchor','start').attr('font-size',11).attr('font-weight','600').attr('fill','#374151').text(s1.name||'After');
  g.append('line').attr('x1',0).attr('x2',0).attr('y1',0).attr('y2',hh).attr('stroke','#E2E8F0').attr('stroke-width',1.5);
  g.append('line').attr('x1',w).attr('x2',w).attr('y1',0).attr('y2',hh).attr('stroke','#E2E8F0').attr('stroke-width',1.5);
  entityLbls.forEach(function(lbl,i){
    var v0=(s0.values||[])[i], v1=(s1.values||[])[i];
    if(v0==null||v1==null) return;
    var slopeInfo=slopes.find(function(s){return s.label===lbl;})||{};
    var col=slopeInfo.color||(slopeInfo.highlight?'#2B4EFF':'#94A3B8');
    var sw=slopeInfo.highlight?2.5:1.5;
    g.append('line').attr('x1',0).attr('y1',ys(v0)).attr('x2',w).attr('y2',ys(v1)).attr('stroke',col).attr('stroke-width',sw);
    g.append('circle').attr('cx',0).attr('cy',ys(v0)).attr('r',5).attr('fill',col).attr('stroke','#fff').attr('stroke-width',1.5);
    g.append('circle').attr('cx',w).attr('cy',ys(v1)).attr('r',5).attr('fill',col).attr('stroke','#fff').attr('stroke-width',1.5);
    g.append('text').attr('x',-10).attr('y',ys(v0)+4).attr('text-anchor','end').attr('font-size',11).attr('fill',col).attr('font-weight',slopeInfo.highlight?'700':'400').text(lbl+' '+fmtK(v0));
    var pct=slopeInfo.change_pct!=null?(' (+'+(slopeInfo.change_pct>0?'+':'')+d3.format('.0f')(slopeInfo.change_pct)+'%)'):'';
    g.append('text').attr('x',w+10).attr('y',ys(v1)+4).attr('text-anchor','start').attr('font-size',11).attr('fill',col).attr('font-weight',slopeInfo.highlight?'700':'400').text(fmtK(v1)+pct);
  });
}

// ── FORECAST LINE ─────────────────────────────────────────────────────────────
function renderForecastLine(el, spec) {
  var d=spec.data, lbls=d.labels||[], series=d.series||[], fsi=d.forecast_start_idx||0;
  if(!lbls.length||!series.length) return;
  var actualSer=series.find(function(s){return s.name==='Actual';});
  var fcstSer=series.find(function(s){return s.name==='Forecast';});
  var ciLow=series.find(function(s){return (s.name||'').indexOf('Low')>=0;});
  var ciHigh=series.find(function(s){return (s.name||'').indexOf('High')>=0;});
  var W=800,H=340,m={top:28,right:110,bottom:50,left:72};
  var w=W-m.left-m.right, hh=H-m.top-m.bottom;
  var svg=mkSvg(el,W,H), g=svg.append('g').attr('transform','translate('+m.left+','+m.top+')');
  var tt=setupTooltip(el);
  var xs=d3.scalePoint().domain(lbls).range([0,w]).padding(0.12);
  var allV=[].concat(
    actualSer?actualSer.values.filter(function(v){return v!=null;}): [],
    fcstSer?fcstSer.values.filter(function(v){return v!=null;}): [],
    ciHigh?ciHigh.values.filter(function(v){return v!=null;}): []
  );
  var yMax=d3.max(allV)*1.18||1;
  var ys=d3.scaleLinear().domain([0,yMax]).range([hh,0]);
  g.select('.domain').remove();
  if(fsi>0) {
    var fLbl=lbls[fsi];
    var fx=xs(fLbl);
    if(fx!=null) {
      g.append('rect').attr('x',fx).attr('y',0).attr('width',w-fx).attr('height',hh).attr('fill','rgba(52,211,153,0.05)');
      g.append('line').attr('x1',fx).attr('x2',fx).attr('y1',0).attr('y2',hh).attr('stroke','#34D399').attr('stroke-width',1.5).attr('stroke-dasharray','5,3');
      g.append('text').attr('x',fx+5).attr('y',-8).attr('font-size',10).attr('fill','#34D399').attr('font-weight','600').text('Forecast →');
    }
  }
  if(ciLow&&ciHigh) {
    var ciData=lbls.map(function(l,i){return {l:l, lo:(ciLow.values||[])[i], hi:(ciHigh.values||[])[i]};}).filter(function(x){return x.lo!=null&&x.hi!=null;});
    if(ciData.length) {
      var band=d3.area().x(function(x){return xs(x.l);}).y0(function(x){return ys(x.lo);}).y1(function(x){return ys(x.hi);});
      g.append('path').datum(ciData).attr('fill','rgba(52,211,153,0.15)').attr('d',band);
    }
  }
  if(actualSer) {
    var actData=lbls.map(function(l,i){return {l:l, v:(actualSer.values||[])[i]};}).filter(function(x){return x.v!=null;});
    var aLine=d3.line().x(function(x){return xs(x.l);}).y(function(x){return ys(x.v);}).curve(d3.curveMonotoneX);
    g.append('path').datum(actData).attr('fill','none').attr('stroke',actualSer.color||'#2B4EFF').attr('stroke-width',2.5).attr('d',aLine);
    actData.forEach(function(x){g.append('circle').attr('cx',xs(x.l)).attr('cy',ys(x.v)).attr('r',3).attr('fill',actualSer.color||'#2B4EFF').attr('stroke','#fff').attr('stroke-width',1).on('mouseover',function(ev){showTT(tt,ev,'<strong>'+x.l+'</strong><br/>'+fmtK(x.v));}).on('mousemove',function(ev){showTT(tt,ev,'<strong>'+x.l+'</strong><br/>'+fmtK(x.v));}).on('mouseout',function(){hideTT(tt);});});
  }
  if(fcstSer) {
    var fcData=lbls.map(function(l,i){return {l:l, v:(fcstSer.values||[])[i]};}).filter(function(x){return x.v!=null;});
    if(actualSer&&fcData.length) {
      var lastAct=lbls.map(function(l,i){return {l:l,v:(actualSer.values||[])[i]};}).filter(function(x){return x.v!=null;}).pop();
      if(lastAct) fcData=[lastAct].concat(fcData);
    }
    var fLine=d3.line().x(function(x){return xs(x.l);}).y(function(x){return ys(x.v);}).curve(d3.curveMonotoneX);
    g.append('path').datum(fcData).attr('fill','none').attr('stroke',fcstSer.color||'#34D399').attr('stroke-width',2.5).attr('stroke-dasharray','6,3').attr('d',fLine);
    fcData.filter(function(x){return (fcstSer.values||[]).indexOf(x.v)>=0||(fcData.indexOf(x)>0);}).forEach(function(x,xi){
      if(xi===0) return;
      g.append('circle').attr('cx',xs(x.l)).attr('cy',ys(x.v)).attr('r',5).attr('fill',fcstSer.color||'#34D399').attr('stroke','#fff').attr('stroke-width',1.5);
      g.append('text').attr('x',xs(x.l)).attr('y',ys(x.v)-10).attr('text-anchor','middle').attr('font-size',10).attr('fill',fcstSer.color||'#34D399').attr('font-weight','700').text(fmtK(x.v));
    });
  }
  var legItems=[];
  if(actualSer) legItems.push({label:'Actual', color:actualSer.color||'#2B4EFF', dash:false});
  if(fcstSer)   legItems.push({label:'Forecast', color:fcstSer.color||'#34D399', dash:true});
  if(ciLow)     legItems.push({label:'80% CI', color:'#34D399', area:true});
  legItems.forEach(function(item,i){
    var lx=w+8, ly=i*18+4;
    if(item.area) { g.append('rect').attr('x',lx).attr('y',ly+2).attr('width',14).attr('height',8).attr('fill','rgba(52,211,153,0.25)').attr('rx',2); }
    else { g.append('line').attr('x1',lx).attr('x2',lx+14).attr('y1',ly+6).attr('y2',ly+6).attr('stroke',item.color).attr('stroke-width',2.5).attr('stroke-dasharray',item.dash?'5,3':'none'); }
    g.append('text').attr('x',lx+18).attr('y',ly+11).attr('font-size',10).attr('fill','#374151').text(item.label);
  });
  var tickEvery=Math.max(1,Math.ceil(lbls.length/12));
  g.append('g').attr('transform','translate(0,'+hh+')').call(d3.axisBottom(xs).tickValues(lbls.filter(function(_,i){return i%tickEvery===0;})));
  g.append('g').call(d3.axisLeft(ys).ticks(5).tickFormat(fmtK));
  cleanAx(g);
}

// ── DISPATCH ──────────────────────────────────────────────────────────────────
function renderChart(chartId) {
  var el=document.getElementById('chart-'+chartId);
  if(!el) return;
  d3.select(el).selectAll('*').remove();
  var spec=window.CHART_SPECS&&window.CHART_SPECS[chartId];
  if(!spec||!spec.data) {
    el.innerHTML='<p style="color:#94A3B8;font-size:12px;padding:20px;text-align:center;">No data for: '+chartId+'</p>';
    return;
  }
  var type=spec.chart_type||'';
  try {
    if      (type==='highlight_line')            renderHighlightLine(el,spec);
    else if (type==='highlight_bar')             renderHighlightBar(el,spec);
    else if (type==='vertical_bar')              renderHighlightBar(el,spec);
    else if (type==='grouped_bar')               renderGroupedBar(el,spec);
    else if (type==='horizontal_bar'||type==='model_comparison_bar') renderHorizontalBar(el,spec);
    else if (type==='waterfall')                 renderWaterfall(el,spec);
    else if (type==='slope'||type==='slopegraph') renderSlopegraph(el,spec);
    else if (type==='forecast_line')             renderForecastLine(el,spec);
    else el.innerHTML='<p style="color:#94A3B8;font-size:12px;padding:20px;text-align:center;">Unsupported type: '+type+'</p>';
  } catch(e) {
    el.innerHTML='<p style="color:#EF4444;font-size:12px;padding:20px;">Error ['+chartId+']: '+e.message+'</p>';
    console.error('D3 render error:', chartId, e);
  }
}

// ── INIT ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  Object.keys(window.CHART_SPECS||{}).forEach(function(id) { renderChart(id); });
});
(function() {
  var t;
  window.addEventListener('resize', function() {
    clearTimeout(t);
    t = setTimeout(function() {
      Object.keys(window.CHART_SPECS||{}).forEach(function(id) { renderChart(id); });
    }, 250);
  });
})();

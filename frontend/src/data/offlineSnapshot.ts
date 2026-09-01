/*
 * Browser-bundled fallback for the public portfolio deployment.
 *
 * The hosted Python API uses Render's free tier and may be unavailable while
 * hibernating.  This fixed, explicitly-labelled demonstration dataset keeps
 * the UI reviewable without presenting generated values as production data.
 */

type EventRow = {
  event_date: string;
  event_timestamp: string;
  user_id: string;
  event_name: string;
  order_id: string | null;
  amount: number;
  channel: string;
  region: string;
  category: string;
  campaign: string;
};

const rows: EventRow[] = [
  ['2026-07-01','2026-07-01 09:00:00','u1','page_view',null,0,'search','上海','服饰','summer'],
  ['2026-07-01','2026-07-01 09:01:00','u1','view_item',null,0,'search','上海','服饰','summer'],
  ['2026-07-01','2026-07-01 09:02:00','u1','add_to_cart',null,0,'search','上海','服饰','summer'],
  ['2026-07-01','2026-07-01 09:03:00','u1','begin_checkout',null,0,'search','上海','服饰','summer'],
  ['2026-07-01','2026-07-01 09:04:00','u1','purchase','o1',199,'search','上海','服饰','summer'],
  ['2026-07-01','2026-07-01 10:00:00','u2','page_view',null,0,'social','北京','数码','launch'],
  ['2026-07-01','2026-07-01 10:01:00','u2','view_item',null,0,'social','北京','数码','launch'],
  ['2026-07-01','2026-07-01 10:02:00','u2','add_to_cart',null,0,'social','北京','数码','launch'],
  ['2026-07-02','2026-07-02 11:00:00','u3','page_view',null,0,'organic','广州','美妆','organic'],
  ['2026-07-02','2026-07-02 11:01:00','u3','view_item',null,0,'organic','广州','美妆','organic'],
  ['2026-07-02','2026-07-02 11:02:00','u3','add_to_cart',null,0,'organic','广州','美妆','organic'],
  ['2026-07-02','2026-07-02 11:03:00','u3','begin_checkout',null,0,'organic','广州','美妆','organic'],
  ['2026-07-03','2026-07-03 12:00:00','u4','page_view',null,0,'ads','深圳','家居','promo'],
  ['2026-07-03','2026-07-03 12:01:00','u4','view_item',null,0,'ads','深圳','家居','promo'],
  ['2026-07-03','2026-07-03 12:02:00','u4','add_to_cart',null,0,'ads','深圳','家居','promo'],
  ['2026-07-03','2026-07-03 12:03:00','u4','begin_checkout',null,0,'ads','深圳','家居','promo'],
  ['2026-07-03','2026-07-03 12:04:00','u4','purchase','o2',399,'ads','深圳','家居','promo'],
  ['2026-07-08','2026-07-08 09:00:00','u1','page_view',null,0,'search','上海','服饰','summer'],
  ['2026-07-08','2026-07-08 09:01:00','u1','purchase','o3',129,'search','上海','服饰','summer'],
  ['2026-07-09','2026-07-09 14:00:00','u5','page_view',null,0,'invite','西安','运动','referral'],
].map(([event_date,event_timestamp,user_id,event_name,order_id,amount,channel,region,category,campaign]) => ({
  event_date,event_timestamp,user_id,event_name,order_id,amount,channel,region,category,campaign,
})) as EventRow[];

const capabilities = {
  overview:{enabled:true,reason:null}, trend:{enabled:true,reason:null},
  funnel:{enabled:true,reason:null}, retention:{enabled:true,reason:null},
  rfm:{enabled:true,reason:null}, channel:{enabled:true,reason:null},
  campaign:{enabled:true,reason:null}, region:{enabled:true,reason:null},
  institution:{enabled:false,reason:'需要机构字段'}, quality:{enabled:true,reason:null},
  gmv:{enabled:true,reason:null},
};

const metrics = {
  users:{name:'用户数',aggregation:'distinct_count',field:'user_id',owner:'经营分析',version:'1.0.0'},
  events:{name:'事件数',aggregation:'count',owner:'数据产品',version:'1.0.0'},
  orders:{name:'订单数',aggregation:'distinct_count',field:'order_id',filter:"event_name = 'purchase'",owner:'经营分析',version:'1.0.0'},
  gmv:{name:'GMV',aggregation:'sum',field:'amount',filter:"event_name = 'purchase'",owner:'经营分析',version:'1.0.0'},
  avg_order_amount:{name:'平均订单金额',aggregation:'average',field:'amount',filter:"event_name = 'purchase'",owner:'经营分析',version:'1.0.0'},
  aov_derived:{name:'客单价（派生）',aggregation:'derived',owner:'指标治理',version:'1.0.0'},
  conversion_rate:{name:'购买转化率',aggregation:'ratio',unit:'percent',owner:'增长分析',version:'1.0.0'},
};

const dataset = {
  id:'demo_ecommerce', name:'模拟电商事件 · 演示快照',
  description:'内置固定小数据，仅用于评审交互和指标逻辑，不代表真实业务结论。',
  version:'1.0.0-snapshot', status:'demo', source_type:'browser_snapshot', available:true,
  mappings:{user_id:'user_id',event_id:['event_timestamp','event_name','user_id'],order_id:'order_id',time:'event_timestamp',amount:'amount',channel:'channel',region:'region',campaign:'campaign',event_type:'event_name',category:'category'},
  dimensions:['channel','region','category','campaign','event_name'], metrics,
  quality_rules:[{id:'user_not_null',type:'non_null',field:'user_id',severity:'error'},{id:'amount_non_negative',type:'range',field:'amount',severity:'error'},{id:'event_domain',type:'accepted_values',field:'event_name',severity:'error'}],
  lineage:{nodes:['browser.snapshot','ods.events','dwd.events','dws.user_daily','ads.business_kpi'],edges:[['browser.snapshot','ods.events'],['ods.events','dwd.events'],['dwd.events','dws.user_daily'],['dws.user_daily','ads.business_kpi']]},
  capabilities,
};

const unavailable = (id:string,name:string,source_type:string,error:string) => ({id,name,description:error,source_type,available:false,error,capabilities:{...capabilities,funnel:{enabled:false,reason:error},retention:{enabled:false,reason:error}}});

function scalarMetric(metricId:string, source:EventRow[]):number {
  const purchases=source.filter(r=>r.event_name==='purchase');
  if(metricId==='users') return new Set(source.map(r=>r.user_id)).size;
  if(metricId==='events') return source.length;
  if(metricId==='orders') return new Set(purchases.map(r=>r.order_id)).size;
  if(metricId==='gmv') return purchases.reduce((s,r)=>s+r.amount,0);
  if(metricId==='avg_order_amount'||metricId==='aov_derived') return purchases.reduce((s,r)=>s+r.amount,0)/new Set(purchases.map(r=>r.order_id)).size;
  if(metricId==='conversion_rate') return new Set(purchases.map(r=>r.user_id)).size/new Set(source.map(r=>r.user_id)).size;
  throw new Error(`演示快照不包含指标 ${metricId}`);
}

function metricResult(url:URL):unknown {
  const parts=url.pathname.split('/'); const metricId=parts.at(-1) as string;
  const dimension=url.searchParams.get('dimension');
  const resultRows = dimension
    ? [...new Set(rows.map(r=>String(r[dimension as keyof EventRow])))].map(value=>({[dimension]:value,value:scalarMetric(metricId,rows.filter(r=>String(r[dimension as keyof EventRow])===value))}))
    : [{value:scalarMetric(metricId,rows)}];
  return {dataset_id:'demo_ecommerce',metric_id:metricId,metric_name:metrics[metricId as keyof typeof metrics]?.name,rows:resultRows,generated_sql:'-- offline review snapshot; the live API generates parameterized DuckDB SQL'};
}

export function offlineJson(path:string):unknown {
  const url=new URL(path,'https://snapshot.local');
  if(url.pathname==='/api/v1/datasets') return [dataset,unavailable('ga4_ecommerce','GA4 官方电商样例','parquet','需要可用的后端与官方数据导入'),unavailable('hmda_2025_de','HMDA 2025 Delaware','parquet','需要可用的后端以查询 55,183 条真实申请')];
  if(url.pathname==='/api/v1/datasets/demo_ecommerce') return dataset;
  if(url.pathname.endsWith('/schema')) return Object.keys(rows[0]).map(column_name=>({column_name,column_type:typeof rows[0][column_name as keyof EventRow]==='number'?'DOUBLE':'VARCHAR'}));
  if(url.pathname.endsWith('/preview')) return rows.slice(0,Number(url.searchParams.get('limit')||5));
  if(url.pathname.includes('/metrics/')) return metricResult(url);
  if(url.pathname.endsWith('/quality')) return {dataset_id:'demo_ecommerce',rules:3,passed:3,warnings:0,failed:0,checks:[{id:'user_not_null',type:'non_null',field:'user_id',severity:'error',status:'passed',failures:0},{id:'amount_non_negative',type:'range',field:'amount',severity:'error',status:'passed',failures:0},{id:'event_domain',type:'accepted_values',field:'event_name',severity:'error',status:'passed',failures:0}]};
  if(url.pathname.endsWith('/funnel')) return {dataset_id:'demo_ecommerce',steps:['page_view','view_item','add_to_cart','begin_checkout','purchase'].map(step=>({step,users:new Set(rows.filter(r=>r.event_name===step).map(r=>r.user_id)).size}))};
  throw new Error(`离线快照不支持 ${path}`);
}

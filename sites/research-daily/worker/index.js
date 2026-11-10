const ASSETS = __RESEARCH_DAILY_ASSETS__;
const SIGNALS = new Set(['interested', 'more', 'less', 'question', 'ai_question']);
const SOURCES = new Set(['site', 'gemini', 'other']);

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {status, headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
}

function userId(request) {
  return request.headers.get('oai-authenticated-user-id') || '';
}

function textContent(content) {
  return {content:[{type:'text',text:typeof content === 'string' ? content : JSON.stringify(content, null, 2)}]};
}

async function saveFeedback(request, env) {
  const user = userId(request);
  if (!user) return json({error:'需要通过 Research Daily 的私有访问身份提交反馈。'}, 401);
  let body;
  try { body = await request.json(); } catch { return json({error:'请求内容不是有效 JSON。'}, 400); }
  const paperId = String(body.paperId || '').trim().slice(0, 160);
  const title = String(body.title || '').trim().slice(0, 1000);
  const briefDate = String(body.briefDate || '').trim().slice(0, 32);
  const signal = String(body.signal || '').trim();
  const note = String(body.note || '').trim().slice(0, 4000);
  const source = String(body.source || 'site').trim();
  if (!paperId || !SIGNALS.has(signal) || !SOURCES.has(source)) return json({error:'反馈类型或论文标识无效。'}, 400);
  if ((signal === 'question' || source === 'gemini') && !note) return json({error:'问题反馈或 Gemini 片段不能为空。'}, 400);
  const result = await env.DB.prepare('INSERT INTO feedback (user_id,paper_id,paper_title,brief_date,signal,note,source) VALUES (?,?,?,?,?,?,?)')
    .bind(user,paperId,title,briefDate,signal,note,source).run();
  return json({saved:true,id:result.meta?.last_row_id ?? null}, 201);
}

async function readFeedback(request, env, args = {}) {
  const user = userId(request);
  if (!user) throw new Error('Authenticated Research Daily user required.');
  const paperId = String(args.paper_id || '').trim();
  const limit = Math.max(1, Math.min(Number(args.limit) || 100, 500));
  let statement;
  if (paperId) {
    statement = env.DB.prepare('SELECT id,paper_id,paper_title,brief_date,signal,note,source,created_at FROM feedback WHERE user_id=? AND paper_id=? ORDER BY created_at DESC,id DESC LIMIT ?').bind(user,paperId,limit);
  } else {
    statement = env.DB.prepare('SELECT id,paper_id,paper_title,brief_date,signal,note,source,created_at FROM feedback WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT ?').bind(user,limit);
  }
  const result = await statement.all();
  return result.results || [];
}

async function handleMcp(request, env) {
  let rpc;
  try { rpc = await request.json(); } catch { return json({jsonrpc:'2.0',id:null,error:{code:-32700,message:'Parse error'}}, 400); }
  const reply = (result) => json({jsonrpc:'2.0',id:rpc.id ?? null,result});
  if (rpc.method === 'server/discover') return reply({supportedVersions:['2026-07-28'],capabilities:{tools:{}}});
  if (rpc.method === 'tools/list') return reply({tools:[
    {name:'list_research_feedback',description:'Read the signed-in owner’s Research Daily feedback so future paper selection and summaries can adapt to their interests.',inputSchema:{type:'object',properties:{paper_id:{type:'string'},limit:{type:'integer',minimum:1,maximum:500}},additionalProperties:false}},
    {name:'record_external_questions',description:'Save only question excerpts the user explicitly chose to import from Gemini or another reading assistant. Never import an entire private conversation unless the user explicitly requests it.',inputSchema:{type:'object',required:['paper_id','questions'],properties:{paper_id:{type:'string'},paper_title:{type:'string'},brief_date:{type:'string'},questions:{type:'string',maxLength:4000},source:{type:'string',enum:['gemini','other']}},additionalProperties:false}}
  ]});
  if (rpc.method !== 'tools/call') return json({jsonrpc:'2.0',id:rpc.id ?? null,error:{code:-32601,message:'Method not found'}}, 404);
  const name = rpc.params?.name;
  const args = rpc.params?.arguments || {};
  try {
    if (name === 'list_research_feedback') return reply(textContent({feedback:await readFeedback(request,env,args)}));
    if (name === 'record_external_questions') {
      const synthetic = new Request(request.url,{method:'POST',headers:request.headers,body:JSON.stringify({paperId:args.paper_id,title:args.paper_title,briefDate:args.brief_date,signal:'ai_question',note:args.questions,source:args.source || 'gemini'})});
      const saved = await saveFeedback(synthetic,env);
      const payload = await saved.json();
      return reply({...textContent(payload),isError:!saved.ok});
    }
    return reply({...textContent('Unknown tool'),isError:true});
  } catch (error) {
    return reply({...textContent(error instanceof Error ? error.message : 'Tool failed'),isError:true});
  }
}

function serveAsset(pathname) {
  let path = decodeURIComponent(pathname);
  if (path.endsWith('/')) path += 'index.html';
  if (path === '') path = '/index.html';
  const asset = ASSETS[path];
  if (!asset) return new Response('Not found',{status:404});
  return new Response(asset.body,{headers:{'content-type':asset.type,'cache-control':asset.type.startsWith('text/html') ? 'no-cache' : 'public, max-age=300'}});
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/feedback' && request.method === 'POST') return saveFeedback(request,env);
    if (url.pathname === '/api/feedback' && request.method === 'GET') {
      try { return json({feedback:await readFeedback(request,env,{paper_id:url.searchParams.get('paper_id'),limit:url.searchParams.get('limit')})}); }
      catch (error) { return json({error:error.message},401); }
    }
    if (url.pathname === '/mcp' && request.method === 'POST') return handleMcp(request,env);
    if (request.method !== 'GET' && request.method !== 'HEAD') return new Response('Method not allowed',{status:405});
    return serveAsset(url.pathname);
  }
};

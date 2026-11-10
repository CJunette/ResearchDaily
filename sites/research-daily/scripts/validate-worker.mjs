import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';

const root=resolve(import.meta.dirname,'..');
const source=await readFile(resolve(root,'dist/server/index.js'),'utf8');
const mod=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
assert.equal(typeof mod.default?.fetch,'function');
const calls=[];
const DB={prepare(sql){return{bind(...values){return{async run(){calls.push({sql,values});return{meta:{last_row_id:1}}},async all(){return{results:[]}}}}}}};
const page=await mod.default.fetch(new Request('https://example.test/'),{DB});
assert.equal(page.status,200); assert.match(await page.text(),/RESEARCH DAILY/);
const saved=await mod.default.fetch(new Request('https://example.test/api/feedback',{method:'POST',headers:{'content-type':'application/json','oai-authenticated-user-id':'test-user'},body:JSON.stringify({paperId:'p_test',title:'Test',briefDate:'2026-11-10',signal:'more',note:'More work like this',source:'site'})}),{DB});
assert.equal(saved.status,201); assert.equal(calls.length,1);
const discover=await mod.default.fetch(new Request('https://example.test/mcp',{method:'POST',headers:{'content-type':'application/json','oai-authenticated-user-id':'test-user'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'server/discover'})}),{DB});
assert.equal(discover.status,200); assert.match(await discover.text(),/2026-07-28/);
console.log('Worker, feedback API, and MCP endpoint validated');

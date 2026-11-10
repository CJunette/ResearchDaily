import {createServer} from 'node:http';
import worker from '../dist/server/index.js';

const rows=[];
const DB={prepare(sql){return{bind(...values){return{async run(){rows.push({id:rows.length+1,user_id:values[0],paper_id:values[1],paper_title:values[2],brief_date:values[3],signal:values[4],note:values[5],source:values[6],created_at:new Date().toISOString()});return{meta:{last_row_id:rows.length}}},async all(){return{results:rows.slice().reverse()}}}}}}};
const port=Number(process.argv[2]||4173);
createServer(async(req,res)=>{
  const chunks=[];for await(const chunk of req)chunks.push(chunk);
  const headers=new Headers();for(const [key,value] of Object.entries(req.headers))if(value)headers.set(key,Array.isArray(value)?value.join(','):value);
  headers.set('oai-authenticated-user-id','local-preview-user');
  const body=chunks.length?Buffer.concat(chunks):undefined;
  const request=new Request(`http://127.0.0.1:${port}${req.url}`,{method:req.method,headers,body,...(body?{duplex:'half'}:{})});
  const response=await worker.fetch(request,{DB});res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));
}).listen(port,'127.0.0.1',()=>console.log(`Preview http://127.0.0.1:${port}`));

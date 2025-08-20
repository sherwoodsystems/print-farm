import type { RequestHandler } from '@sveltejs/kit';

export const GET: RequestHandler = async () => {
\treturn new Response(
\t\tJSON.stringify({
\t\t\tmessage: 'Print Farm API',
\t\t\tendpoints: {
\t\t\t\t'POST /api/labels/generate': 'Proxy to remote generator to create PDF without printing'
\t\t\t}
\t\t}),
\t\t{ status: 200, headers: { 'content-type': 'application/json' } }
\t);
};



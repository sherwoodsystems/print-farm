import type { RequestHandler } from '@sveltejs/kit';

export const GET: RequestHandler = async () => {
	return new Response(JSON.stringify({
		message: 'Print Farm API',
		endpoints: {
			'POST /api/labels/generate': 'Proxy to remote generator to create PDF without printing'
		}
	}), { status: 200, headers: { 'content-type': 'application/json' } });
};



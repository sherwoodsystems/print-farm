import type { RequestHandler } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

type LabelSize = '1x3' | '2x4' | '4x6';
type TargetPrinter = 'small' | 'medium' | 'large' | 'url';

interface GenerateRequestBody {
	template?: 'simple' | 'product' | 'shipping';
	data?: Record<string, unknown>;
	labelSize?: LabelSize;
	target?: TargetPrinter;
	copies?: number;
	url?: string;
	dryRun?: boolean;
}

const PRINTERS: Record<'small' | 'medium' | 'large', string> = {
	small: env.PRINTER_SMALL_URL || 'http://100.105.161.92:3001',
	medium: env.PRINTER_MEDIUM_URL || 'http://100.105.161.92:3002',
	large: env.PRINTER_LARGE_URL || 'http://100.105.161.92:3003'
};

export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = (await request.json()) as GenerateRequestBody;

	const template = body.template ?? 'simple';
	const data = body.data ?? {};
	const labelSize: LabelSize = (body.labelSize as LabelSize) ?? '2x4';
	const copies = Number.isFinite(body.copies) && (body.copies as number) > 0 ? (body.copies as number) : 1;
	const target: TargetPrinter = body.target ?? 'small';
	const dryRun = Boolean(body.dryRun);

	let baseUrl: string | undefined;
	if (target === 'url') {
		baseUrl = body.url;
	} else {
		baseUrl = PRINTERS[target];
	}

	if (!baseUrl) {
		return new Response(
			JSON.stringify({ error: 'No printer URL configured for target', target }),
			{ status: 400, headers: { 'content-type': 'application/json' } }
		);
	}

	const generatorPayload = { template, data, labelSize, copies };

	if (dryRun) {
		return new Response(
			JSON.stringify({ ok: true, dryRun: true, target, url: `${baseUrl}/generate`, payload: generatorPayload }),
			{ status: 200, headers: { 'content-type': 'application/json' } }
		);
	}

	try {
		const res = await fetch(`${baseUrl}/generate`, {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify(generatorPayload)
		});

		const text = await res.text();
		let json: unknown;
		try {
			json = JSON.parse(text);
		} catch {
			json = { raw: text };
		}

		if (!res.ok) {
			return new Response(
				JSON.stringify({ error: 'Remote service error', status: res.status, body: json }),
				{ status: 502, headers: { 'content-type': 'application/json' } }
			);
		}

		// Forward the remote JSON response directly so the client gets the same
		// structure as when calling the generator service via curl.
		return new Response(
			JSON.stringify(json),
			{ status: 200, headers: { 'content-type': 'application/json' } }
		);
	} catch (error) {
		return new Response(
			JSON.stringify({ error: 'Failed to reach generator service', details: (error as Error).message }),
			{ status: 500, headers: { 'content-type': 'application/json' } }
		);
	}
};



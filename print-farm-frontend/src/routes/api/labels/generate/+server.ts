import type { RequestHandler } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

type LabelSize = '3x1' | '102x51mm' | '4x6.25';
type TargetPrinter = 'small' | 'medium' | 'large' | 'url';

interface GenerateRequestBody {
	template?: 'simple' | 'product' | 'shipping';
	data?: Record<string, unknown>;
	labelSize?: LabelSize;
	target?: TargetPrinter;
	copies?: number;
	url?: string;
	dryRun?: boolean;
	print?: boolean;  // New parameter to trigger printing on the backend
}

// Map printer targets to URLs - small green (3x1) is at .92:3001
const PRINTERS: Record<'small' | 'medium' | 'large', string> = {
	small: env.PRINTER_SMALL_URL || 'http://100.105.161.92:3001',   // Small green 3x1
	medium: env.PRINTER_MEDIUM_URL || 'http://100.105.161.92:3002',  // Medium white 102x51mm
	large: env.PRINTER_LARGE_URL || 'http://100.105.161.92:3003'    // Large shipping 4x6.25
};

export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = (await request.json()) as GenerateRequestBody;

	const template = body.template ?? 'simple';
	const data = body.data ?? {};
	const labelSize: LabelSize = (body.labelSize as LabelSize) ?? '3x1';  // Default to small green
	const copies = Number.isFinite(body.copies) && (body.copies as number) > 0 ? (body.copies as number) : 1;
	const target: TargetPrinter = body.target ?? 'small';
	const dryRun = Boolean(body.dryRun);
	const print = Boolean(body.print);  // New parameter

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

	const generatorPayload = { template, data, labelSize, copies, print };

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



import type { RequestHandler } from '@sveltejs/kit';
import { PRINTER_SMALL_URL, PRINTER_MEDIUM_URL, PRINTER_LARGE_URL } from '$env/static/private';

type LabelSize = '1x3' | '2x4' | '4x6';
type TargetPrinter = 'small' | 'medium' | 'large' | 'url';

interface GenerateRequestBody {
\ttemplate?: 'simple' | 'product' | 'shipping';
\tdata?: Record<string, unknown>;
\tlabelSize?: LabelSize;
\ttarget?: TargetPrinter;
\tcopies?: number;
\turl?: string; // when target === 'url'
\tdryRun?: boolean; // if true, do not call remote service; return the payload that would be sent
}

const PRINTERS: Record<'small' | 'medium' | 'large', string> = {
\tsmall: PRINTER_SMALL_URL || 'http://100.105.161.92:3001',
\tmedium: PRINTER_MEDIUM_URL || 'http://100.105.161.92:3002',
\tlarge: PRINTER_LARGE_URL || 'http://100.105.161.92:3003'
};

export const POST: RequestHandler = async ({ request, fetch }) => {
\tconst body = (await request.json()) as GenerateRequestBody;

\tconst template = body.template ?? 'simple';
\tconst data = body.data ?? {};
\tconst labelSize: LabelSize = (body.labelSize as LabelSize) ?? '2x4';
\tconst copies = Number.isFinite(body.copies) && (body.copies as number) > 0 ? (body.copies as number) : 1;
\tconst target: TargetPrinter = body.target ?? 'small';
\tconst dryRun = Boolean(body.dryRun);

\tlet baseUrl: string | undefined;
\tif (target === 'url') {
\t\tbaseUrl = body.url;
\t} else {
\t\tbaseUrl = PRINTERS[target];
\t}

\tif (!baseUrl) {
\t\treturn new Response(
\t\t\tJSON.stringify({ error: 'No printer URL configured for target', target }),
\t\t\t{ status: 400, headers: { 'content-type': 'application/json' } }
\t\t);
\t}

\t// Normalized payload for the Windows generator service
\tconst generatorPayload = {
\t\t// service on Windows container should expose POST /generate to only create PDF
\t\ttemplate,
\t\tdata,
\t\tlabelSize,
\t\tcopies
\t};

\tif (dryRun) {
\t\treturn new Response(
\t\t\tJSON.stringify({ ok: true, dryRun: true, target, url: `${baseUrl}/generate`, payload: generatorPayload }),
\t\t\t{ status: 200, headers: { 'content-type': 'application/json' } }
\t\t);
\t}

\ttry {
\t\tconst res = await fetch(`${baseUrl}/generate`, {
\t\t\tmethod: 'POST',
\t\t\theaders: { 'content-type': 'application/json' },
\t\t\tbody: JSON.stringify(generatorPayload)
\t\t});

\t\tconst text = await res.text();
\t\tlet json: unknown;
\t\ttry {
\t\t\tjson = JSON.parse(text);
\t\t} catch {
\t\t\tjson = { raw: text };
\t\t}

\t\tif (!res.ok) {
\t\t\treturn new Response(
\t\t\t\tJSON.stringify({ error: 'Remote service error', status: res.status, body: json }),
\t\t\t\t{ status: 502, headers: { 'content-type': 'application/json' } }
\t\t\t);
\t\t}

\t\treturn new Response(
\t\t\tJSON.stringify({ ok: true, target, response: json }),
\t\t\t{ status: 200, headers: { 'content-type': 'application/json' } }
\t\t);
\t} catch (error) {
\t\treturn new Response(
\t\t\tJSON.stringify({ error: 'Failed to reach generator service', details: (error as Error).message }),
\t\t\t{ status: 500, headers: { 'content-type': 'application/json' } }
\t\t);
\t}
};



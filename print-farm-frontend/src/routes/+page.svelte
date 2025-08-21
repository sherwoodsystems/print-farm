<script lang="ts">
	let form = {
		printer: 'small',
		labelSize: '3x1',  // Default to small green
		template: 'simple',
		copies: 1,
		content: 'Hello from Print Farm',
		align: 'center',
		textAlign: 'center',
		fontSize: '12pt',
		dryRun: false,
		print: false
	};

	let result: unknown = null;

	async function submitGenerate(event: SubmitEvent) {
		event.preventDefault();
		const payload = {
			target: form.printer as 'small' | 'medium' | 'large',
			labelSize: form.labelSize as '3x1' | '102x51mm' | '4x6.25',
			template: form.template as 'simple' | 'product' | 'shipping',
			copies: Number(form.copies) || 1,
			dryRun: Boolean(form.dryRun),
			print: Boolean(form.print),
			data: {
				content: form.content,
				align: form.align,
				textAlign: form.textAlign,
				fontSize: form.fontSize
			}
		};

		const res = await fetch('/api/labels/generate', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify(payload)
		});
		result = await res.json();
	}
</script>

<div class="max-w-3xl mx-auto p-6">
	<h1 class="text-2xl font-semibold mb-6">Print Farm - Generate Label (no print)</h1>

	<form onsubmit={submitGenerate} class="space-y-6">
		<fieldset class="border rounded-md p-4">
			<legend class="text-sm font-medium px-2">Target</legend>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
				<label class="flex flex-col gap-1">
					<span class="text-sm text-gray-600">Printer</span>
					<select bind:value={form.printer} class="rounded border-gray-300 focus:ring-2 focus:ring-blue-500">
						<option value="small">Small Green (3x1)</option>
						<option value="medium">Medium White (102x51mm)</option>
						<option value="large">Large Shipping (4x6.25)</option>
					</select>
				</label>
			</div>
		</fieldset>

		<fieldset class="border rounded-md p-4">
			<legend class="text-sm font-medium px-2">Label</legend>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
				<label class="flex flex-col gap-1">
					<span class="text-sm text-gray-600">Size</span>
					<select bind:value={form.labelSize} class="rounded border-gray-300 focus:ring-2 focus:ring-blue-500">
						<option value="3x1">3" x 1" (Small Green)</option>
						<option value="102x51mm">102mm x 51mm (Medium White)</option>
						<option value="4x6.25">4" x 6.25" (Shipping Label)</option>
					</select>
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-sm text-gray-600">Template</span>
					<select bind:value={form.template} class="rounded border-gray-300 focus:ring-2 focus:ring-blue-500">
						<option value="simple">Simple</option>
						<option value="product">Product</option>
						<option value="shipping">Shipping</option>
					</select>
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-sm text-gray-600">Copies</span>
					<input type="number" min="1" bind:value={form.copies} class="rounded border-gray-300 focus:ring-2 focus:ring-blue-500" />
				</label>
				<label class="flex items-center gap-2">
					<input type="checkbox" bind:checked={form.dryRun} class="rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500" />
					<span class="text-sm text-gray-600">Dry run (do not call remote)</span>
				</label>
				<label class="flex items-center gap-2">
					<input type="checkbox" bind:checked={form.print} class="rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500" />
					<span class="text-sm text-gray-600">Print to default printer</span>
				</label>
			</div>
		</fieldset>

		<fieldset class="border rounded-md p-4">
			<legend class="text-sm font-medium px-2">Simple template data</legend>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
				<label class="flex flex-col gap-1 sm:col-span-2">
					<span class="text-sm text-gray-600">Content</span>
					<textarea rows="3" bind:value={form.content} class="rounded border-gray-300 focus:ring-2 focus:ring-blue-500"></textarea>
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-sm text-gray-600">Align</span>
					<select bind:value={form.align} class="rounded border-gray-300 focus:ring-2 focus:ring-blue-500">
						<option value="start">start</option>
						<option value="center">center</option>
						<option value="end">end</option>
					</select>
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-sm text-gray-600">Text Align</span>
					<select bind:value={form.textAlign} class="rounded border-gray-300 focus:ring-2 focus:ring-blue-500">
						<option value="left">left</option>
						<option value="center">center</option>
						<option value="right">right</option>
					</select>
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-sm text-gray-600">Font Size</span>
					<input type="text" bind:value={form.fontSize} placeholder="e.g., 12pt" class="rounded border-gray-300 focus:ring-2 focus:ring-blue-500" />
				</label>
			</div>
		</fieldset>

		<div class="pt-2">
			<button type="submit" class="inline-flex items-center px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500">
				{form.print ? 'Generate & Print' : 'Generate PDF'}
			</button>
		</div>
	</form>

	{#if result}
		<div class="mt-8 space-y-3">
			<h2 class="text-lg font-semibold">Response</h2>
			{#if (result as any)?.url}
				<div class="border rounded">
					<iframe src={(result as any).url} class="w-full" style="height: 480px;" title="Preview"></iframe>
				</div>
			{/if}
			<pre class="bg-gray-100 p-3 rounded overflow-auto text-sm">{JSON.stringify(result, null, 2)}</pre>
		</div>
	{/if}
</div>



<script lang="ts">
	let form = {
		printer: 'small',
		labelSize: '2x4',
		template: 'simple',
		copies: 1,
		content: 'Hello from Print Farm',
		align: 'center',
		textAlign: 'center',
		fontSize: '12pt',
		dryRun: true
	};

	let result: unknown = null;

	async function submitGenerate(event: SubmitEvent) {
		event.preventDefault();
		const payload = {
			target: form.printer as 'small' | 'medium' | 'large',
			labelSize: form.labelSize as '1x3' | '2x4' | '4x6',
			template: form.template as 'simple' | 'product' | 'shipping',
			copies: Number(form.copies) || 1,
			dryRun: Boolean(form.dryRun),
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

<h1>Print Farm - Generate Label (no print)</h1>

<form onsubmit={submitGenerate}>
	<fieldset>
		<legend>Target</legend>
		<label>
			Printer
			<select bind:value={form.printer}>
				<option value="small">Small (1x3)</option>
				<option value="medium">Medium (2x4)</option>
				<option value="large">Large (4x6)</option>
			</select>
		</label>
	</fieldset>

	<fieldset>
		<legend>Label</legend>
		<label>
			Size
			<select bind:value={form.labelSize}>
				<option value="1x3">1x3</option>
				<option value="2x4">2x4</option>
				<option value="4x6">4x6</option>
			</select>
		</label>
		<label>
			Template
			<select bind:value={form.template}>
				<option value="simple">Simple</option>
				<option value="product">Product</option>
				<option value="shipping">Shipping</option>
			</select>
		</label>
		<label>
			Copies
			<input type="number" min="1" bind:value={form.copies} />
		</label>
		<label>
			Dry run (do not call remote)
			<input type="checkbox" bind:checked={form.dryRun} />
		</label>
	</fieldset>

	<fieldset>
		<legend>Simple template data</legend>
		<label>
			Content
			<textarea rows="4" bind:value={form.content}></textarea>
		</label>
		<div>
			<label>Align
				<select bind:value={form.align}>
					<option value="start">start</option>
					<option value="center">center</option>
					<option value="end">end</option>
				</select>
			</label>
			<label>Text Align
				<select bind:value={form.textAlign}>
					<option value="left">left</option>
					<option value="center">center</option>
					<option value="right">right</option>
				</select>
			</label>
			<label>Font Size
				<input type="text" bind:value={form.fontSize} placeholder="e.g., 12pt" />
			</label>
		</div>
	</fieldset>

	<button type="submit">Generate PDF</button>
</form>

{#if result}
	<h2>Response</h2>
	<pre>{JSON.stringify(result, null, 2)}</pre>
{/if}


